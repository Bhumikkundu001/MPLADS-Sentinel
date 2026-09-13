"""
Phase 4 — deterministic, explainable risk scoring for real MPLADS records.

Every signal is a plain rule over actual stored/raw fields — no randomness,
no jitter, no ML in this module (Isolation Forest anomaly detection lives in
anomaly_engine.py and is intentionally kept separate from risk_score).

This is a decision-support signal generator, not a fraud detector. Indicator
text must never claim wrongdoing — see SYSTEM_PROMPT-style language used
throughout the rest of the app (Potential Risk / Requires Review / Monitor
Closely / Decision Support).
"""
from datetime import date

# ── Evaluation date for "long-pending recommendation" (Signal 3) ──────────
# Fixed and documented rather than "today", so batch re-runs are reproducible.
# Chosen to be just after the latest date observed anywhere in either real
# dataset (max observed: 2026-08-25, Rajya Sabha `recommended_date`), so every
# real elapsed-day calculation is meaningful and none go negative.
EVALUATION_DATE = date(2026, 9, 1)

HIGH_THRESHOLD = 70
MEDIUM_THRESHOLD = 40


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def compute_iqr_bounds(values):
    """Tukey's fence: upper_bound = Q3 + 1.5 * IQR. `values` must be a
    pandas Series of non-null numeric values (one house, one field)."""
    if len(values) == 0:
        return {"q1": None, "q3": None, "iqr": None, "upper_bound": None, "n": 0}
    q1 = float(values.quantile(0.25))
    q3 = float(values.quantile(0.75))
    iqr = q3 - q1
    upper = q3 + 1.5 * iqr
    return {"q1": round(q1, 2), "q3": round(q3, 2), "iqr": round(iqr, 2), "upper_bound": round(upper, 2), "n": int(len(values))}


def score_record(record, outlier_bounds, sanctioned_date):
    """
    record: dict with recommended_amount, sanctioned_amount, expenditure,
            proposed_date, actual_completion, is_reported_complete (all in
            the same units/format as the Work model / staging DB row).
    outlier_bounds: {"recommended": {...}, "sanctioned": {...}} for this house,
                    from compute_iqr_bounds().
    sanctioned_date: raw source `sanctioned_date` string or None (pulled from
                    work_raw_source — not a Work model column).

    Returns (risk_score_or_None, risk_level_or_None, risk_status_or_None,
             indicators_list, signals_evaluated_count).
    """
    recommended = record.get("recommended_amount")
    sanctioned = record.get("sanctioned_amount")
    expenditure = record.get("expenditure")
    proposed_date = _parse_date(record.get("proposed_date"))
    actual_completion = _parse_date(record.get("actual_completion"))
    is_reported_complete = record.get("is_reported_complete")

    indicators = []
    score = 0
    signals_evaluated = 0

    # Signal 1: recommended vs sanctioned deviation
    if recommended is not None and recommended > 0 and sanctioned is not None:
        signals_evaluated += 1
        deviation_pct = abs(recommended - sanctioned) / recommended * 100
        points = 30 if deviation_pct > 25 else (15 if deviation_pct > 10 else 0)
        if points > 0:
            score += points
            indicators.append({
                "type": "recommendation_sanction_deviation",
                "message": (
                    f"Sanctioned amount ({sanctioned:.2f} lakhs) deviates {deviation_pct:.1f}% "
                    f"from the recommended amount ({recommended:.2f} lakhs), exceeding the "
                    f"{'25%' if points == 30 else '10%'} review threshold."
                ),
                "observed_value": round(deviation_pct, 1),
                "threshold": 25 if points == 30 else 10,
                "points": points,
            })

    # Signal 2: expenditure vs sanctioned
    if sanctioned is not None and sanctioned > 0 and expenditure is not None:
        signals_evaluated += 1
        if expenditure > sanctioned:
            points = 30
            msg = (
                f"Expenditure ({expenditure:.2f} lakhs) exceeds the sanctioned amount "
                f"({sanctioned:.2f} lakhs)."
            )
        elif expenditure > 0.9 * sanctioned:
            points = 15
            msg = (
                f"Expenditure ({expenditure:.2f} lakhs) has reached "
                f"{expenditure / sanctioned * 100:.0f}% of the sanctioned amount "
                f"({sanctioned:.2f} lakhs), exceeding the 90% monitoring threshold."
            )
        else:
            points = 0
            msg = None
        if points > 0:
            score += points
            indicators.append({
                "type": "expenditure_sanction_ratio",
                "message": msg,
                "observed_value": round(expenditure / sanctioned * 100, 1),
                "threshold": 100 if points == 30 else 90,
                "points": points,
            })

    # Signal 3: long-pending recommendation
    if proposed_date is not None and is_reported_complete is not True:
        signals_evaluated += 1
        elapsed_days = (EVALUATION_DATE - proposed_date).days
        if elapsed_days > 365:
            points = 20
            score += points
            indicators.append({
                "type": "long_pending_recommendation",
                "message": (
                    f"{elapsed_days} days have elapsed since the recommendation date "
                    f"({proposed_date.isoformat()}) as of the {EVALUATION_DATE.isoformat()} "
                    f"evaluation date, and the work is not reported complete, exceeding the "
                    f"365-day review threshold."
                ),
                "observed_value": elapsed_days,
                "threshold": 365,
                "points": points,
            })

    # Signal 4: statistical amount outlier (Tukey's fence, per-house)
    outlier_hits = []
    rec_bounds = outlier_bounds.get("recommended", {})
    sanc_bounds = outlier_bounds.get("sanctioned", {})
    if recommended is not None and rec_bounds.get("upper_bound") is not None:
        signals_evaluated += 1
        if recommended > rec_bounds["upper_bound"]:
            outlier_hits.append(("recommended_amount", recommended, rec_bounds["upper_bound"]))
    if sanctioned is not None and sanc_bounds.get("upper_bound") is not None:
        signals_evaluated += 1
        if sanctioned > sanc_bounds["upper_bound"]:
            outlier_hits.append(("sanctioned_amount", sanctioned, sanc_bounds["upper_bound"]))
    if outlier_hits:
        points = 15
        score += points
        parts = [
            f"{field} ({val:.2f} lakhs) exceeds this house's statistical upper bound "
            f"({bound:.2f} lakhs, Q3 + 1.5×IQR)"
            for field, val, bound in outlier_hits
        ]
        indicators.append({
            "type": "statistical_amount_outlier",
            "message": "; ".join(parts) + ".",
            "observed_value": [round(v, 2) for _, v, _ in outlier_hits],
            "threshold": [round(b, 2) for _, _, b in outlier_hits],
            "points": points,
        })

    # Signal 5: workflow inconsistency
    signals_evaluated += 1  # always evaluable — every field involved has a defined (possibly None) value
    inconsistencies = []
    if is_reported_complete is True and actual_completion is None:
        inconsistencies.append("reported complete but completion date is missing")
    if actual_completion is not None and is_reported_complete is not True:
        inconsistencies.append("completion date present but work is not reported complete")
    if sanctioned is not None and not sanctioned_date:
        inconsistencies.append("sanctioned amount present but sanctioned date is missing")
    if actual_completion is not None and proposed_date is not None and actual_completion < proposed_date:
        inconsistencies.append("completion date precedes the recommendation date")
    sanc_date_parsed = _parse_date(sanctioned_date)
    if actual_completion is not None and sanc_date_parsed is not None and actual_completion < sanc_date_parsed:
        inconsistencies.append("completion date precedes the sanction date")

    if inconsistencies:
        points = 10
        score += points
        indicators.append({
            "type": "workflow_inconsistency",
            "message": "Data inconsistency flagged: " + "; ".join(inconsistencies) + ".",
            "observed_value": inconsistencies,
            "threshold": None,
            "points": points,
        })

    if signals_evaluated == 0:
        return None, None, None, [], 0

    score = max(0, min(100, score))
    if score >= HIGH_THRESHOLD:
        level, status = "High", "Requires Review"
    elif score >= MEDIUM_THRESHOLD:
        level, status = "Medium", "Monitor Closely"
    else:
        level, status = "Low", "Normal"

    return score, level, status, indicators, signals_evaluated
