"""
Phase 4 — batch computation of real, explainable risk scores and anomaly
flags for the 38,265 real MPLADS records in the staging database.

Reads: mplads_sentinel_staging.db (works, work_raw_source) — read + write.
Never touches mplads_sentinel.db (production/demo).
Never modifies the 92 demo_seed rows even in staging (there aren't any in
staging, but the UPDATE is scoped by data_source as a hard guarantee anyway).

Idempotent: recomputes and overwrites only
(risk_score, risk_level, risk_status, anomaly_score, is_anomaly,
 risk_indicators_json, risk_computed_at) for rows where
data_source IN ('lok_sabha_real', 'rajya_sabha_real'). No other column,
and no other data_source, is ever touched.

Run: python compute_phase4_risk.py
"""
import json
import sqlite3
from datetime import datetime, date

import pandas as pd

import risk_engine
import anomaly_engine

STAGING_DB = "mplads_sentinel_staging.db"
PRODUCTION_DB = "mplads_sentinel.db"
REAL_SOURCES = ["lok_sabha_real", "rajya_sabha_real"]


def load_sanctioned_dates(con):
    raw = pd.read_sql_query(
        "SELECT work_id, data_source, raw_json FROM work_raw_source "
        "WHERE data_source IN ('lok_sabha_real', 'rajya_sabha_real')",
        con,
    )
    lookup = {}
    for _, row in raw.iterrows():
        try:
            payload = json.loads(row["raw_json"])
        except (TypeError, ValueError):
            payload = {}
        lookup[(row["work_id"], row["data_source"])] = payload.get("sanctioned_date")
    return lookup


def _clean_record(rec):
    """pandas gives float64 columns NaN (not None) for SQL NULL — normalize to real
    None here so every `is None` / `is not None` check in risk_engine/anomaly_engine
    behaves correctly. (DataFrame-level aggregate ops like .quantile() are computed
    separately, before this, and are unaffected by this per-record cleanup.)"""
    return {
        k: (None if isinstance(v, float) and pd.isnull(v) else v)
        for k, v in rec.items()
    }


def compute_for_house(df, house_label, sanctioned_date_lookup):
    rec_bounds = risk_engine.compute_iqr_bounds(df["recommended_amount"].dropna())
    sanc_bounds = risk_engine.compute_iqr_bounds(df["sanctioned_amount"].dropna())
    outlier_bounds = {"recommended": rec_bounds, "sanctioned": sanc_bounds}

    records = [_clean_record(r) for r in df.to_dict("records")]
    risk_results = []
    for rec in records:
        sanc_date = sanctioned_date_lookup.get((rec["id"], rec["data_source"]))
        result = risk_engine.score_record(rec, outlier_bounds, sanc_date)
        risk_results.append(result)

    anomaly_results, anomaly_config = anomaly_engine.compute_anomalies_for_house(records)

    return risk_results, anomaly_results, outlier_bounds, anomaly_config


def main():
    con = sqlite3.connect(STAGING_DB)

    works_df = pd.read_sql_query(
        "SELECT id, data_source, recommended_amount, sanctioned_amount, expenditure, "
        "proposed_date, actual_completion, is_reported_complete FROM works "
        "WHERE data_source IN ('lok_sabha_real', 'rajya_sabha_real')",
        con,
    )
    # SQLite BOOLEAN is stored/returned as integer 0/1, not Python bool — `is True` /
    # `is not True` identity checks elsewhere would silently misfire on an int. Normalize
    # to real Python bool/None right at the data boundary so downstream comparisons are safe.
    works_df["is_reported_complete"] = works_df["is_reported_complete"].apply(
        lambda v: None if v is None else bool(v)
    )
    print(f"Loaded {len(works_df)} real records from staging (lok_sabha_real + rajya_sabha_real)")

    sanctioned_date_lookup = load_sanctioned_dates(con)
    print(f"Loaded {len(sanctioned_date_lookup)} raw sanctioned_date lookups")

    ls_df = works_df[works_df.data_source == "lok_sabha_real"].reset_index(drop=True)
    rs_df = works_df[works_df.data_source == "rajya_sabha_real"].reset_index(drop=True)

    computed_at = datetime.utcnow().isoformat()
    updates = []
    all_outlier_bounds = {}
    all_anomaly_config = {}

    for house_label, house_df in [("Lok Sabha", ls_df), ("Rajya Sabha", rs_df)]:
        print(f"\nComputing risk + anomaly for {house_label} ({len(house_df)} records)...")
        risk_results, anomaly_results, outlier_bounds, anomaly_config = compute_for_house(
            house_df, house_label, sanctioned_date_lookup
        )
        all_outlier_bounds[house_label] = outlier_bounds
        all_anomaly_config[house_label] = anomaly_config

        for i, rec in enumerate(house_df.to_dict("records")):
            risk_score, risk_level, risk_status, indicators, n_signals = risk_results[i]
            anomaly_score, is_anomaly, anomaly_indicator = anomaly_results[i]

            all_indicators = list(indicators)
            if anomaly_indicator is not None:
                all_indicators.append(anomaly_indicator)

            updates.append({
                "id": rec["id"],
                "data_source": rec["data_source"],
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_status": risk_status,
                "anomaly_score": anomaly_score,
                "is_anomaly": is_anomaly,
                "risk_indicators_json": json.dumps(all_indicators),
                "risk_computed_at": computed_at if risk_score is not None else None,
                "_signals_evaluated": n_signals,
                "_house": house_label,
            })

    print(f"\nWriting {len(updates)} rows back to staging (scoped to real data_source values only)...")
    cur = con.cursor()
    with con:
        for u in updates:
            cur.execute(
                """UPDATE works SET
                     risk_score = ?, risk_level = ?, risk_status = ?,
                     anomaly_score = ?, is_anomaly = ?, risk_indicators_json = ?,
                     risk_computed_at = ?
                   WHERE id = ? AND data_source = ?""",
                (
                    u["risk_score"], u["risk_level"], u["risk_status"],
                    u["anomaly_score"], u["is_anomaly"], u["risk_indicators_json"],
                    u["risk_computed_at"], u["id"], u["data_source"],
                ),
            )
    print("Write complete.")

    # Sanity: demo_seed rows in production untouched (we never opened that file)
    prod_con = sqlite3.connect(PRODUCTION_DB)
    prod_count = pd.read_sql_query("SELECT COUNT(*) c FROM works", prod_con).iloc[0]["c"]
    prod_con.close()
    print(f"\nProduction db row count (should be 92, untouched): {prod_count}")

    con.close()

    config = {
        "computed_at": computed_at,
        "evaluation_date": risk_engine.EVALUATION_DATE.isoformat(),
        "risk_thresholds": {"high": risk_engine.HIGH_THRESHOLD, "medium": risk_engine.MEDIUM_THRESHOLD},
        "outlier_bounds": all_outlier_bounds,
        "anomaly_config": all_anomaly_config,
    }
    with open("phase4_computation_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, default=str)
    print("\nWrote phase4_computation_config.json")

    return updates, all_outlier_bounds, all_anomaly_config, computed_at


if __name__ == "__main__":
    main()
