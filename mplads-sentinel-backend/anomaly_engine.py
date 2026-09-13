"""
Phase 4 — Isolation Forest anomaly detection for real MPLADS records, fit
separately per house (Lok Sabha / Rajya Sabha have meaningfully different
financial scales — see Phase 0 audit).

The anomaly_score produced here is NOT a probability of fraud. It is a
percentile-ranked, per-house Isolation Forest decision_function value:
LOWER values are MORE anomalous, preserving the existing Work model column's
documented convention ("anomaly_score: lower = more anomalous").
`is_anomaly` is a relative-ranking flag (contamination=0.05 → roughly the
most unusual 5% of records in that house), not an absolute determination.
"""
from datetime import date

import numpy as np
from sklearn.ensemble import IsolationForest

from risk_engine import EVALUATION_DATE

RANDOM_STATE = 42
CONTAMINATION = 0.05
N_ESTIMATORS = 200


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def build_features(records):
    """
    records: list of dicts with recommended_amount, sanctioned_amount,
             expenditure, proposed_date (all from the staging Work rows).

    Returns (X, feature_names, per_record_raw) where per_record_raw carries
    the untransformed numbers used later for explanation text.
    """
    recommended = np.array([r.get("recommended_amount") or 0.0 for r in records], dtype=float)

    sanctioned_raw = [r.get("sanctioned_amount") for r in records]
    sanctioned_missing = np.array([1.0 if v is None else 0.0 for v in sanctioned_raw])
    sanctioned_median = np.median([v for v in sanctioned_raw if v is not None]) if any(v is not None for v in sanctioned_raw) else 0.0
    sanctioned_filled = np.array([v if v is not None else sanctioned_median for v in sanctioned_raw], dtype=float)

    expenditure_raw = [r.get("expenditure") for r in records]
    expenditure_missing = np.array([1.0 if v is None else 0.0 for v in expenditure_raw])
    expenditure_median = np.median([v for v in expenditure_raw if v is not None]) if any(v is not None for v in expenditure_raw) else 0.0
    expenditure_filled = np.array([v if v is not None else expenditure_median for v in expenditure_raw], dtype=float)

    deviation_pct = []
    deviation_missing = []
    for r in records:
        rec = r.get("recommended_amount")
        sanc = r.get("sanctioned_amount")
        if rec is not None and rec > 0 and sanc is not None:
            deviation_pct.append(abs(rec - sanc) / rec * 100)
            deviation_missing.append(0.0)
        else:
            deviation_pct.append(None)
            deviation_missing.append(1.0)
    dev_median = np.median([v for v in deviation_pct if v is not None]) if any(v is not None for v in deviation_pct) else 0.0
    deviation_filled = np.array([v if v is not None else dev_median for v in deviation_pct], dtype=float)
    deviation_missing = np.array(deviation_missing)

    exp_ratio = []
    ratio_missing = []
    for r in records:
        sanc = r.get("sanctioned_amount")
        exp = r.get("expenditure")
        if sanc is not None and sanc > 0 and exp is not None:
            exp_ratio.append(exp / sanc)
            ratio_missing.append(0.0)
        else:
            exp_ratio.append(None)
            ratio_missing.append(1.0)
    ratio_median = np.median([v for v in exp_ratio if v is not None]) if any(v is not None for v in exp_ratio) else 0.0
    ratio_filled = np.array([v if v is not None else ratio_median for v in exp_ratio], dtype=float)
    ratio_missing = np.array(ratio_missing)

    elapsed_days = []
    for r in records:
        pd_ = _parse_date(r.get("proposed_date"))
        elapsed_days.append((EVALUATION_DATE - pd_).days if pd_ is not None else 0)
    elapsed_days = np.array(elapsed_days, dtype=float)

    log_recommended = np.log1p(np.clip(recommended, 0, None))
    log_sanctioned = np.log1p(np.clip(sanctioned_filled, 0, None))
    log_expenditure = np.log1p(np.clip(expenditure_filled, 0, None))

    X = np.column_stack([
        log_recommended,
        log_sanctioned,
        log_expenditure,
        deviation_filled,
        ratio_filled,
        elapsed_days,
        sanctioned_missing,
        expenditure_missing,
        deviation_missing,
        ratio_missing,
    ])
    feature_names = [
        "log_recommended_amount", "log_sanctioned_amount", "log_expenditure",
        "deviation_pct", "expenditure_ratio", "elapsed_days",
        "sanctioned_missing", "expenditure_missing", "deviation_missing", "ratio_missing",
    ]

    raw = {
        "recommended_amount": recommended,
        "sanctioned_amount": sanctioned_filled,
        "sanctioned_amount_present": 1 - sanctioned_missing,
        "expenditure": expenditure_filled,
        "expenditure_present": 1 - expenditure_missing,
        "expenditure_ratio": ratio_filled,
        "expenditure_ratio_present": 1 - ratio_missing,
        "elapsed_days": elapsed_days,
    }
    return X, feature_names, raw


def run_isolation_forest(X):
    model = IsolationForest(
        n_estimators=N_ESTIMATORS,
        contamination=CONTAMINATION,
        random_state=RANDOM_STATE,
    )
    model.fit(X)
    decision = model.decision_function(X)  # lower = more anomalous
    is_outlier = model.predict(X) == -1
    return decision, is_outlier


def percentile_rank_score(decision):
    """0-100, LOWER = more anomalous (ascending rank of decision_function,
    rescaled to a 0-100 range for readability)."""
    order = np.argsort(decision)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(len(decision))
    pct = ranks / max(len(decision) - 1, 1) * 100
    return np.round(pct, 1)


def explain_anomaly(idx, raw, decision, house_stats):
    """Build feature-level percentile evidence for one flagged record —
    no SHAP, just descriptive statistics against the house's own distribution."""
    reasons = []

    rec_val = raw["recommended_amount"][idx]
    rec_pct = house_stats["recommended_amount_percentile_fn"](rec_val)
    if rec_pct >= 90:
        reasons.append(
            f"Recommended amount ({rec_val:.2f} lakhs) is higher than {rec_pct:.0f}% of works in its house."
        )

    if raw["sanctioned_amount_present"][idx]:
        sanc_val = raw["sanctioned_amount"][idx]
        sanc_pct = house_stats["sanctioned_amount_percentile_fn"](sanc_val)
        if sanc_pct >= 90:
            reasons.append(
                f"Sanctioned amount ({sanc_val:.2f} lakhs) is higher than {sanc_pct:.0f}% of works in its house."
            )

    if raw["expenditure_ratio_present"][idx]:
        ratio_val = raw["expenditure_ratio"][idx]
        ratio_pct = house_stats["expenditure_ratio_percentile_fn"](ratio_val)
        if ratio_pct >= 90:
            reasons.append(
                f"Expenditure-to-sanctioned ratio ({ratio_val:.2f}) is higher than {ratio_pct:.0f}% of works in its house."
            )

    elapsed_val = raw["elapsed_days"][idx]
    elapsed_pct = house_stats["elapsed_days_percentile_fn"](elapsed_val)
    if elapsed_pct >= 90:
        reasons.append(
            f"Elapsed time since recommendation ({elapsed_val:.0f} days) is longer than {elapsed_pct:.0f}% of works in its house."
        )

    missing_flags = []
    if not raw["sanctioned_amount_present"][idx]:
        missing_flags.append("sanctioned amount")
    if not raw["expenditure_present"][idx]:
        missing_flags.append("expenditure")
    if missing_flags:
        reasons.append(
            "Unusual missing-data pattern: " + " and ".join(missing_flags) + " not yet recorded for this work."
        )

    if not reasons:
        reasons.append(
            "Flagged as statistically unusual by the anomaly model based on a combination of "
            "features that are not individually extreme — see raw feature percentiles for detail."
        )

    return {
        "type": "ml_anomaly_evidence",
        "source": "isolation_forest",
        "message": (
            "AI-assisted anomaly signal (Decision Support, not a fraud determination): "
            + " ".join(reasons)
        ),
        "observed_value": None,
        "threshold": None,
        "points": 0,
    }


def make_percentile_fn(values):
    sorted_vals = np.sort(values)

    def fn(v):
        if len(sorted_vals) == 0:
            return 0.0
        idx = np.searchsorted(sorted_vals, v, side="right")
        return idx / len(sorted_vals) * 100

    return fn


def compute_anomalies_for_house(records):
    """records: list of dicts (Work-row-shaped). Returns list of
    (anomaly_score, is_anomaly, anomaly_indicator_or_None) aligned to input order."""
    X, feature_names, raw = build_features(records)
    decision, is_outlier = run_isolation_forest(X)
    anomaly_scores = percentile_rank_score(decision)

    house_stats = {
        "recommended_amount_percentile_fn": make_percentile_fn(raw["recommended_amount"]),
        "sanctioned_amount_percentile_fn": make_percentile_fn(
            raw["sanctioned_amount"][raw["sanctioned_amount_present"] == 1]
        ),
        "expenditure_ratio_percentile_fn": make_percentile_fn(
            raw["expenditure_ratio"][raw["expenditure_ratio_present"] == 1]
        ),
        "elapsed_days_percentile_fn": make_percentile_fn(raw["elapsed_days"]),
    }

    results = []
    for i in range(len(records)):
        if is_outlier[i]:
            indicator = explain_anomaly(i, raw, decision, house_stats)
        else:
            indicator = None
        results.append((float(anomaly_scores[i]), bool(is_outlier[i]), indicator))
    return results, {
        "n_estimators": N_ESTIMATORS,
        "contamination": CONTAMINATION,
        "random_state": RANDOM_STATE,
        "feature_names": feature_names,
        "n_records": len(records),
        "n_flagged": int(is_outlier.sum()),
    }
