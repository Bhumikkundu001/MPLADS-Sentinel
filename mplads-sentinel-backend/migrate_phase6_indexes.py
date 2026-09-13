"""
Phase 6 index migration: add the missing index on work_similarities.work_id
in the STAGING database only.

Audit finding: work_similarities had zero indexes beyond the implicit rowid,
so GET /works/{work_id}/similar was doing a full table scan across all
191,325 rows on every request. This is additive-only, staging-only —
mplads_sentinel.db (production/demo, 92 rows) is never opened.

Run: python migrate_phase6_indexes.py
"""
import sqlite3

STAGING_DB = "mplads_sentinel_staging.db"


def main():
    con = sqlite3.connect(STAGING_DB)
    cur = con.cursor()

    before = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='work_similarities'"
    ).fetchall()
    print(f"work_similarities indexes before: {before}")

    cur.execute("CREATE INDEX IF NOT EXISTS ix_work_similarities_work_id ON work_similarities(work_id)")
    con.commit()

    after = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='work_similarities'"
    ).fetchall()
    print(f"work_similarities indexes after: {after}")

    row_count = cur.execute("SELECT COUNT(*) FROM work_similarities").fetchone()[0]
    print(f"work_similarities row count (unchanged, should be 191325): {row_count}")

    con.close()


if __name__ == "__main__":
    main()
