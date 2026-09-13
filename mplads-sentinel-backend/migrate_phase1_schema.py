"""
Phase 1 schema migration: add real-dataset-migration columns to `works`.

Adds 6 new columns (data_source, source_row_id, dataset_version, raw_status,
is_reported_complete, risk_computed_at), backfills data_source="demo_seed" on
all existing rows, and adds indexes. Additive only — does not touch or remove
any existing row or column. Safe to re-run (skips columns/indexes that already
exist).
"""
import sqlite3

from app.database import DATABASE_URL

DB_PATH = DATABASE_URL.replace("sqlite:///", "").lstrip("./")

NEW_COLUMNS = [
    ("data_source", "VARCHAR(30)"),
    ("source_row_id", "VARCHAR(30)"),
    ("dataset_version", "VARCHAR(30)"),
    ("raw_status", "VARCHAR(100)"),
    ("is_reported_complete", "BOOLEAN"),
    ("risk_computed_at", "DATETIME"),
]

INDEXES = [
    ("ix_works_state", "state"),
    ("ix_works_status", "status"),
    ("ix_works_risk_level", "risk_level"),
    ("ix_works_risk_status", "risk_status"),
    ("ix_works_house", "house"),
    ("ix_works_data_source", "data_source"),
    ("ix_works_is_anomaly", "is_anomaly"),
]


def existing_columns(cur):
    cur.execute("PRAGMA table_info(works)")
    return {row[1] for row in cur.fetchall()}


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    before_count = cur.execute("SELECT COUNT(*) FROM works").fetchone()[0]

    cols = existing_columns(cur)
    for col_name, col_type in NEW_COLUMNS:
        if col_name in cols:
            print(f"skip (exists): {col_name}")
            continue
        cur.execute(f"ALTER TABLE works ADD COLUMN {col_name} {col_type}")
        print(f"added column: {col_name} {col_type}")

    cur.execute(
        "UPDATE works SET data_source = 'demo_seed' WHERE data_source IS NULL"
    )
    print(f"backfilled data_source='demo_seed' on {cur.rowcount} row(s)")

    for index_name, column in INDEXES:
        cur.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON works({column})")
        print(f"ensured index: {index_name} ON works({column})")

    con.commit()

    after_count = cur.execute("SELECT COUNT(*) FROM works").fetchone()[0]
    assert before_count == after_count, (
        f"Row count changed! before={before_count} after={after_count}"
    )
    print(f"row count unchanged: {after_count}")

    con.close()


if __name__ == "__main__":
    main()
