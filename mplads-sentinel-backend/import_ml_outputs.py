import ast
import json
from datetime import datetime

import pandas as pd
from sqlalchemy import delete

from app.database import engine
from app.models.work import Work, WorkSimilarity
from app.database import Base


# ============================================================
# CONFIGURATION
# ============================================================

LS_CSV = r"D:\SIHAIML\MPLADS-ML-Handoff\lok_sabha_ml_output.csv"
RS_CSV = r"D:\SIHAIML\MPLADS-ML-Handoff\rajya_sabha_ml_output.csv"

LS_VERSION = "lok_sabha_final_processed_ml_master_v1"
RS_VERSION = "rajya_sabha_final_processed_ml_master_v1"


# ============================================================
# HELPERS
# ============================================================

def safe_str(value):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    value = str(value).strip()
    return value if value else None


def safe_float(value):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value):
    number = safe_float(value)

    if number is None:
        return None

    return int(round(number))


def rupees_to_lakhs(value):
    value = safe_float(value)

    if value is None:
        return None

    return round(value / 100000, 2)


def parse_list(value):
    """
    ML output stores lists as strings such as:
    "['Indicator 1', 'Indicator 2']"
    """

    if value is None:
        return []

    try:
        if pd.isna(value):
            return []
    except (TypeError, ValueError):
        pass

    if isinstance(value, list):
        return value

    text = str(value).strip()

    if not text or text == "[]":
        return []

    try:
        parsed = ast.literal_eval(text)

        if isinstance(parsed, list):
            return parsed

        return []

    except (ValueError, SyntaxError):
        return []


def normalize_risk_level(value):
    value = safe_str(value)

    if not value:
        return "Low"

    mapping = {
        "LOW": "Low",
        "MEDIUM": "Medium",
        "HIGH": "High",
    }

    return mapping.get(value.upper(), value.title())


def normalize_bool(value):
    if isinstance(value, bool):
        return value

    value = safe_str(value)

    if value is None:
        return False

    return value.lower() in {
        "true",
        "1",
        "yes",
        "y",
    }


# ============================================================
# ROW TRANSFORMATION
# ============================================================

def transform_row(row, house, data_source, dataset_version):

    work_id = safe_str(row.get("work_id"))

    # Rajya Sabha has rows where work_id is missing.
    # Preserve those records by deriving an ID from sr_no.
    if not work_id:
        sr_no = safe_str(row.get("sr_no"))

        if not sr_no:
            return None

        work_id = f"RS-SR-{sr_no}"

    recommended_amount = rupees_to_lakhs(
        row.get("recommended_amount_rs")
    )

    sanctioned_amount = rupees_to_lakhs(
        row.get("sanctioned_amount_rs")
    )

    if house == "Lok Sabha":
        expenditure = rupees_to_lakhs(
            row.get("amount_disbursed_rs")
        )
        constituency = safe_str(row.get("constituency"))
    else:
        expenditure = rupees_to_lakhs(
            row.get("expenditure_total_rs")
        )
        constituency = None

    risk_indicators = parse_list(
        row.get("risk_indicators")
    )

    now = datetime.utcnow()

    return {
        "id": work_id,

        "name": (
            safe_str(row.get("work"))
            or safe_str(row.get("work_description"))
            or f"MPLADS Work {work_id}"
        ),

        "description": (
            safe_str(row.get("work_description"))
            or "No description available in source data."
        ),

        "house": house,

        "mp_name": safe_str(row.get("mp_name")),

        "state": safe_str(row.get("state")),

        "constituency": constituency,

        "district": None,

        "category": safe_str(row.get("work_category")),

        "executing_agency": safe_str(row.get("ida")),

        "status": safe_str(row.get("work_status")),

        "recommended_amount": recommended_amount,

        "sanctioned_amount": sanctioned_amount,

        "expenditure": expenditure,

        "proposed_date": safe_str(
            row.get("recommended_date")
        ),

        "expected_completion": None,

        "actual_completion": safe_str(
            row.get("completion_date")
        ),

        "progress": None,

        # ====================================================
        # YOUR VALIDATED ML OUTPUTS
        # ====================================================

        "risk_score": safe_int(
            row.get("risk_score")
        ),

        "risk_level": normalize_risk_level(
            row.get("risk_level")
        ),

        "risk_status": (
            "Requires Review"
            if normalize_risk_level(row.get("risk_level")) == "High"
            else "Normal"
        ),

        "anomaly_score": safe_float(
            row.get("anomaly_score")
        ),

        "is_anomaly": normalize_bool(
            row.get("is_anomaly")
        ),

        "risk_indicators_json": json.dumps(
            risk_indicators,
            ensure_ascii=False
        ),

        "risk_computed_at": now,

        # ====================================================
        # PROVENANCE
        # ====================================================

        "data_source": data_source,

        "source_row_id": safe_str(
            row.get("sr_no")
        ),

        "dataset_version": dataset_version,

        "raw_status": safe_str(
            row.get("work_status")
        ),

        "is_reported_complete": (
            normalize_bool(row.get("completed"))
            if safe_str(row.get("completed")) is not None
            else None
        ),

        "created_at": now,

        "updated_at": now,
    }


# ============================================================
# LOAD CSV
# ============================================================

def load_csv(path, house, data_source, dataset_version):

    print()
    print("=" * 70)
    print(f"Loading {house}")
    print("=" * 70)

    df = pd.read_csv(
        path,
        low_memory=False
    )

    print(f"CSV rows: {len(df)}")

    rows = []

    skipped = 0

    for _, row in df.iterrows():

        transformed = transform_row(
            row,
            house,
            data_source,
            dataset_version
        )

        if transformed is None:
            skipped += 1
            continue

        rows.append(transformed)

    print(f"Transformed rows: {len(rows)}")
    print(f"Skipped rows: {skipped}")

    return rows


# ============================================================
# MAIN IMPORT
# ============================================================

def main():

    print()
    print("=" * 70)
    print("MPLADS SENTINEL — ML OUTPUT IMPORT")
    print("=" * 70)

    print()
    print("IMPORTANT:")
    print("This imports YOUR validated ML outputs.")
    print("It does NOT run another ML/risk algorithm.")
    print()

    # --------------------------------------------------------
    # Create tables if database is empty/new
    # --------------------------------------------------------

    print("Ensuring database tables exist...")

    Base.metadata.create_all(
        bind=engine
    )

    # --------------------------------------------------------
    # Load both ML outputs
    # --------------------------------------------------------

    ls_rows = load_csv(
        LS_CSV,
        "Lok Sabha",
        "lok_sabha_real",
        LS_VERSION
    )

    rs_rows = load_csv(
        RS_CSV,
        "Rajya Sabha",
        "rajya_sabha_real",
        RS_VERSION
    )

    all_rows = ls_rows + rs_rows

    print()
    print("=" * 70)
    print("IMPORT SUMMARY")
    print("=" * 70)

    print(f"Lok Sabha:   {len(ls_rows)}")
    print(f"Rajya Sabha: {len(rs_rows)}")
    print(f"TOTAL:       {len(all_rows)}")

    # --------------------------------------------------------
    # Duplicate protection
    # --------------------------------------------------------

    ids = [row["id"] for row in all_rows]

    duplicate_ids = {
        work_id
        for work_id in ids
        if ids.count(work_id) > 1
    }

    if duplicate_ids:

        print()
        print("ERROR: Duplicate work IDs detected:")
        print(list(duplicate_ids)[:20])

        raise RuntimeError(
            "Duplicate work IDs detected. Import stopped."
        )

    # --------------------------------------------------------
    # Import into the MAIN backend database
    # --------------------------------------------------------

    print()
    print("Writing to MAIN backend database...")
    print("Database:", engine.url)

    with engine.begin() as conn:

        # Remove only previously imported REAL ML records.
        # Demo records, if any, are preserved.
        conn.execute(
            delete(Work.__table__).where(
                Work.__table__.c.data_source.in_(
                    [
                        "lok_sabha_real",
                        "rajya_sabha_real",
                    ]
                )
            )
        )

        # Remove existing similarity relationships
        # associated with real records.
        conn.execute(
            delete(WorkSimilarity.__table__)
        )

        # Insert all ML-scored works
        conn.execute(
            Work.__table__.insert(),
            all_rows
        )

    # --------------------------------------------------------
    # Validate database
    # --------------------------------------------------------

    from app.database import SessionLocal

    db = SessionLocal()

    try:

        total = db.query(Work).count()

        high = (
            db.query(Work)
            .filter(Work.risk_level == "High")
            .count()
        )

        medium = (
            db.query(Work)
            .filter(Work.risk_level == "Medium")
            .count()
        )

        low = (
            db.query(Work)
            .filter(Work.risk_level == "Low")
            .count()
        )

        anomalies = (
            db.query(Work)
            .filter(Work.is_anomaly == True)
            .count()
        )

        print()
        print("=" * 70)
        print("DATABASE VALIDATION")
        print("=" * 70)

        print(f"Total works:     {total}")
        print(f"High risk:       {high}")
        print(f"Medium risk:     {medium}")
        print(f"Low risk:        {low}")
        print(f"Anomalies:       {anomalies}")

        expected_total = 13657 + 24609

        if total != expected_total:
            raise RuntimeError(
                f"Unexpected database count: {total}. "
                f"Expected {expected_total}."
            )

        if high != 138 + 243:
            raise RuntimeError(
                f"Unexpected HIGH count: {high}."
            )

        if medium != 3384 + 4396:
            raise RuntimeError(
                f"Unexpected MEDIUM count: {medium}."
            )

        if low != 10135 + 19970:
            raise RuntimeError(
                f"Unexpected LOW count: {low}."
            )

        print()
        print("SUCCESS: ML outputs match expected validated counts.")

    finally:
        db.close()

    print()
    print("=" * 70)
    print("ML IMPORT COMPLETE")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()