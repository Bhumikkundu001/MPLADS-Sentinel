"""
Phase 2: import and normalize the real Lok Sabha + Rajya Sabha MPLADS datasets
into a separate staging database.

Does NOT touch mplads_sentinel.db (the 92-row demo/production database).
Does NOT compute risk scores, anomaly scores, or similarity — those fields
are left at safe defaults (0 / "Low" / "Normal" / not-yet-scored) for later
phases.

Idempotent: re-running deletes and re-inserts only rows tagged
data_source in ("lok_sabha_real", "rajya_sabha_real") in the staging DB,
so repeated runs never produce duplicates.

Run: python import_phase2_staging.py
"""
import json
import re
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, delete

from app.database import Base
from app.models.work import Work, WorkSimilarity  # noqa: F401 — registers tables on Base

LS_CSV = r"D:\SIHAIML\MPLADS-ML-Handoff\lok_sabha_ml_output.csv"
RS_CSV = r"D:\SIHAIML\MPLADS-ML-Handoff\rajya_sabha_ml_output.csv"

STAGING_DB_FILE = "mplads_sentinel_staging.db"
STAGING_URL = f"sqlite:///./{STAGING_DB_FILE}"

LS_DATASET_VERSION = "lok_sabha_final_processed_ml_master_v1"
RS_DATASET_VERSION = "rajya_sabha_final_processed_ml_master_v1"

CHUNK_SIZE = 2000

# ── Raw-source companion table (staging-only, separate MetaData so it never
# touches the shared `Base` used by the production database) ─────────────────
raw_metadata = MetaData()
work_raw_source = Table(
    "work_raw_source",
    raw_metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("work_id", String(30), index=True),
    Column("data_source", String(30), index=True),
    Column("raw_json", Text),
)


def safe_str(v):
    if v is None or (isinstance(v, float) and pd.isnull(v)):
        return None
    s = str(v).strip()
    return s or None


def to_lakhs(v):
    if v is None or (isinstance(v, float) and pd.isnull(v)):
        return None
    try:
        return round(float(v) / 100000, 2)
    except (TypeError, ValueError):
        return None


def clean_rs_mp_name(name):
    cleaned = safe_str(name)
    if not cleaned:
        return None
    cleaned = re.sub(r"\s*\(\d{4}-\d{2,4}\)", "", cleaned).strip()
    return cleaned or None


def truncate_words(text, limit=100):
    if len(text) <= limit:
        return text
    truncated = text[:limit]
    cut = truncated.rfind(" ")
    if cut > 0:
        truncated = truncated[:cut]
    return truncated + "\u2026"


def derive_name(anchor_id, work_field, description):
    desc = safe_str(description)
    if desc:
        return truncate_words(desc)

    w = safe_str(work_field)
    if w:
        phrase = w
        if anchor_id:
            tail = anchor_id.rsplit("/", 1)[-1]
            marker = f"{tail}-"
            idx = w.find(marker)
            if idx != -1:
                phrase = w[idx + len(marker):].strip()
        phrase = re.sub(r"^NA-\s*", "", phrase).strip()
        if phrase:
            return truncate_words(phrase)

    return f"MPLADS Work {anchor_id}" if anchor_id else "MPLADS Work (unidentified)"


def transform_row(row, house, data_source, dataset_version, errors):
    sr_no = safe_str(row.get("sr_no"))
    state = safe_str(row.get("state"))

    if not state:
        errors.append({
            "sr_no": sr_no,
            "reason": "missing state — likely a non-data footer/summary row, not a real record",
        })
        return None

    raw_work_id = safe_str(row.get("work_id"))
    if raw_work_id:
        work_id = raw_work_id
    else:
        if not sr_no:
            errors.append({"sr_no": sr_no, "reason": "missing both work_id and sr_no — cannot derive an id"})
            return None
        work_id = f"RS-SR-{sr_no}"

    mp_name_raw = safe_str(row.get("mp_name"))
    mp_name = clean_rs_mp_name(mp_name_raw) if house == "Rajya Sabha" else mp_name_raw

    name = derive_name(raw_work_id, row.get("work"), row.get("work_description"))
    description = safe_str(row.get("work_description")) or "No description available in source data."

    raw_status = safe_str(row.get("work_status"))
    status = raw_status  # identity mapping: raw values are already clean, short display strings

    completed_val = row.get("completed")
    is_reported_complete = None
    if completed_val is not None and not (isinstance(completed_val, float) and pd.isnull(completed_val)):
        is_reported_complete = bool(int(completed_val))

    recommended_amount = to_lakhs(row.get("recommended_amount_rs"))
    sanctioned_amount = to_lakhs(row.get("sanctioned_amount_rs"))

    if house == "Lok Sabha":
        expenditure = to_lakhs(row.get("amount_disbursed_rs"))
        constituency = safe_str(row.get("constituency"))
    else:
        expenditure = to_lakhs(row.get("expenditure_total_rs"))
        constituency = None

    now = datetime.utcnow()

    return {
        "id": work_id,
        "name": name,
        "description": description,
        "house": house,
        "mp_name": mp_name,
        "state": state,
        "constituency": constituency,
        "district": None,
        "category": safe_str(row.get("work_category")),
        "executing_agency": safe_str(row.get("ida")),
        "status": status,
        "recommended_amount": recommended_amount,
        "sanctioned_amount": sanctioned_amount,
        "expenditure": expenditure,
        "proposed_date": safe_str(row.get("recommended_date")),
        "expected_completion": None,
        "actual_completion": safe_str(row.get("completion_date")),
        "progress": None,
        "risk_score": 0,
        "risk_level": "Low",
        "risk_status": "Normal",
        "anomaly_score": 0.0,
        "is_anomaly": False,
        "risk_indicators_json": "[]",
        "risk_computed_at": None,
        "data_source": data_source,
        "source_row_id": sr_no,
        "dataset_version": dataset_version,
        "raw_status": raw_status,
        "is_reported_complete": is_reported_complete,
        "created_at": now,
        "updated_at": now,
    }, sr_no


def load_house(csv_path, house, data_source, dataset_version):
    df = pd.read_csv(csv_path, low_memory=False)
    errors = []
    rows = []
    raw_rows = []

    records = df.to_dict("records")
    for row in records:
        result = transform_row(row, house, data_source, dataset_version, errors)
        if result is None:
            continue
        work_row, sr_no = result
        rows.append(work_row)

        clean_raw = {k: (None if isinstance(v, float) and pd.isnull(v) else v) for k, v in row.items()}
        raw_rows.append({
            "work_id": work_row["id"],
            "data_source": data_source,
            "raw_json": json.dumps(clean_raw, default=str),
        })

    return df, rows, raw_rows, errors


def check_duplicates(rows, label):
    seen = {}
    dups = []
    for r in rows:
        if r["id"] in seen:
            dups.append(r["id"])
        seen[r["id"]] = True
    if dups:
        print(f"  WARNING: {len(dups)} duplicate id(s) within {label}: {dups[:10]}{'...' if len(dups) > 10 else ''}")
    return dups


def main():
    print("=" * 70)
    print("PHASE 2 — Real dataset staging import")
    print("=" * 70)

    print(f"\nReading Lok Sabha CSV: {LS_CSV}")
    ls_df, ls_rows, ls_raw, ls_errors = load_house(LS_CSV, "Lok Sabha", "lok_sabha_real", LS_DATASET_VERSION)
    print(f"  CSV rows: {len(ls_df)} | valid transformed: {len(ls_rows)} | skipped: {len(ls_errors)}")

    print(f"\nReading Rajya Sabha CSV: {RS_CSV}")
    rs_df, rs_rows, rs_raw, rs_errors = load_house(RS_CSV, "Rajya Sabha", "rajya_sabha_real", RS_DATASET_VERSION)
    print(f"  CSV rows: {len(rs_df)} | valid transformed: {len(rs_rows)} | skipped: {len(rs_errors)}")

    if ls_errors:
        print("\n  Lok Sabha skipped rows:")
        for e in ls_errors:
            print(f"    sr_no={e['sr_no']!r}: {e['reason']}")
    if rs_errors:
        print("\n  Rajya Sabha skipped rows:")
        for e in rs_errors:
            print(f"    sr_no={e['sr_no']!r}: {e['reason']}")

    print("\nChecking for duplicate ids...")
    ls_dups = check_duplicates(ls_rows, "Lok Sabha")
    rs_dups = check_duplicates(rs_rows, "Rajya Sabha")

    combined_ids = [r["id"] for r in ls_rows] + [r["id"] for r in rs_rows]
    cross_dups = len(combined_ids) - len(set(combined_ids))
    print(f"  Cross-house duplicate ids: {cross_dups}")

    generated_rs_ids = sum(1 for r in rs_rows if r["id"].startswith("RS-SR-"))
    real_rs_ids = len(rs_rows) - generated_rs_ids
    print(f"  Rajya Sabha: {real_rs_ids} real work_id used, {generated_rs_ids} synthetic RS-SR-* generated")

    print(f"\nConnecting to staging database: {STAGING_URL}")
    staging_engine = create_engine(STAGING_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=staging_engine)
    raw_metadata.create_all(bind=staging_engine)

    print("Clearing any prior lok_sabha_real / rajya_sabha_real rows (idempotent re-import)...")
    with staging_engine.begin() as conn:
        conn.execute(
            delete(Work.__table__).where(
                Work.__table__.c.data_source.in_(["lok_sabha_real", "rajya_sabha_real"])
            )
        )
        conn.execute(
            delete(work_raw_source).where(
                work_raw_source.c.data_source.in_(["lok_sabha_real", "rajya_sabha_real"])
            )
        )

    all_rows = ls_rows + rs_rows
    all_raw = ls_raw + rs_raw

    print(f"\nInserting {len(all_rows)} work rows in chunks of {CHUNK_SIZE}...")
    with staging_engine.begin() as conn:
        for i in range(0, len(all_rows), CHUNK_SIZE):
            chunk = all_rows[i:i + CHUNK_SIZE]
            conn.execute(Work.__table__.insert(), chunk)
        print(f"  inserted {len(all_rows)} work rows")

        for i in range(0, len(all_raw), CHUNK_SIZE):
            chunk = all_raw[i:i + CHUNK_SIZE]
            conn.execute(work_raw_source.insert(), chunk)
        print(f"  inserted {len(all_raw)} raw-source rows")

    print("\nImport complete.")
    print(f"  Lok Sabha imported: {len(ls_rows)}")
    print(f"  Rajya Sabha imported: {len(rs_rows)}")
    print(f"  Total imported: {len(all_rows)}")


if __name__ == "__main__":
    main()
