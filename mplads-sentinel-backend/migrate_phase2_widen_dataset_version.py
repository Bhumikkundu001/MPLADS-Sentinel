"""
Widen `works.dataset_version` from VARCHAR(30) to VARCHAR(60) in the STAGING
database only (mplads_sentinel_staging.db). Does not touch mplads_sentinel.db.

SQLite has no ALTER COLUMN, so this rebuilds the `works` table with the
updated schema (matching app/models/work.py, already updated) and copies
every row across unchanged. Indexes are dropped before the rename and
recreated by Base.metadata.create_all() against the rebuilt table.

Run: python migrate_phase2_widen_dataset_version.py
"""
import sqlite3

from sqlalchemy import create_engine

from app.database import Base
from app.models.work import Work, WorkSimilarity  # noqa: F401 — registers tables on Base

STAGING_DB_FILE = "mplads_sentinel_staging.db"
STAGING_URL = f"sqlite:///./{STAGING_DB_FILE}"

INDEXES = [
    "ix_works_state",
    "ix_works_status",
    "ix_works_risk_level",
    "ix_works_risk_status",
    "ix_works_house",
    "ix_works_data_source",
    "ix_works_is_anomaly",
]

COLUMNS = [
    "id", "name", "description", "house", "mp_name", "state", "constituency", "district",
    "category", "executing_agency", "status", "recommended_amount", "sanctioned_amount",
    "expenditure", "proposed_date", "expected_completion", "actual_completion", "progress",
    "risk_score", "risk_level", "risk_status", "anomaly_score", "is_anomaly",
    "risk_indicators_json", "risk_computed_at", "data_source", "source_row_id",
    "dataset_version", "raw_status", "is_reported_complete", "created_at", "updated_at",
]


def main():
    con = sqlite3.connect(STAGING_DB_FILE)
    cur = con.cursor()

    before_count = cur.execute("SELECT COUNT(*) FROM works").fetchone()[0]
    before_versions = cur.execute(
        "SELECT data_source, dataset_version, COUNT(*) FROM works GROUP BY data_source, dataset_version"
    ).fetchall()
    print(f"Before: {before_count} rows")
    print(f"Before dataset_version breakdown: {before_versions}")

    print("\nDropping old indexes on works...")
    for idx in INDEXES:
        cur.execute(f"DROP INDEX IF EXISTS {idx}")
    con.commit()

    print("Renaming works -> works_old_widen...")
    cur.execute("ALTER TABLE works RENAME TO works_old_widen")
    con.commit()
    con.close()

    print("Recreating `works` with widened dataset_version (VARCHAR(60))...")
    engine = create_engine(STAGING_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)  # only `works` is missing now; others already exist
    engine.dispose()

    con = sqlite3.connect(STAGING_DB_FILE)
    cur = con.cursor()

    col_list = ", ".join(COLUMNS)
    print("Copying data into rebuilt works table...")
    cur.execute(f"INSERT INTO works ({col_list}) SELECT {col_list} FROM works_old_widen")
    con.commit()

    after_count = cur.execute("SELECT COUNT(*) FROM works").fetchone()[0]
    assert before_count == after_count, f"Row count changed! before={before_count} after={after_count}"
    print(f"\nRow count preserved: {after_count}")

    print("Dropping temporary works_old_widen...")
    cur.execute("DROP TABLE works_old_widen")
    con.commit()

    print("\nPRAGMA table_info(works) — dataset_version column:")
    for row in cur.execute("PRAGMA table_info(works)").fetchall():
        if row[1] == "dataset_version":
            print(" ", row)

    after_versions = cur.execute(
        "SELECT data_source, dataset_version, COUNT(*) FROM works GROUP BY data_source, dataset_version"
    ).fetchall()
    print(f"After dataset_version breakdown: {after_versions}")
    assert before_versions == after_versions, "dataset_version values changed during rebuild!"
    print("\ndataset_version values confirmed intact.")

    con.close()


if __name__ == "__main__":
    main()
