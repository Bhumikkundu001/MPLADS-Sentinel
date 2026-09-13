import os
import sqlite3
from datetime import datetime

from sqlalchemy import create_engine, text
from app.database import Base
from app.models.user import User
from app.models.work import Work, WorkSimilarity


SOURCE_DB = "mplads_sentinel.db"
TARGET_URL = os.getenv("POSTGRES_MIGRATION_URL")

EXPECTED_USERS = 2
EXPECTED_WORKS = 38266
EXPECTED_SIMILARITIES = 191325


def normalize_database_url(url):
    if url.startswith("postgres://"):
        return url.replace(
            "postgres://",
            "postgresql+psycopg://",
            1,
        )

    if url.startswith("postgresql://"):
        return url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )

    return url


def parse_datetime(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    value = str(value).strip()

    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def get_sqlite_columns(connection, table_name):
    rows = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return [row[1] for row in rows]


def main():
    print("=" * 70)
    print("MPLADS SENTINEL — SAFE SQLITE → POSTGRESQL MIGRATION")
    print("=" * 70)

    if not TARGET_URL:
        raise RuntimeError(
            "POSTGRES_MIGRATION_URL is not set."
        )

    if not os.path.exists(SOURCE_DB):
        raise RuntimeError(
            f"Source database not found: {SOURCE_DB}"
        )

    target_url = normalize_database_url(TARGET_URL)

    print()
    print("Source database:", SOURCE_DB)
    print("Target database: PostgreSQL")
    print()

    # ------------------------------------------------------------
    # Connect to source SQLite — READ ONLY
    # ------------------------------------------------------------

    source = sqlite3.connect(
        f"file:{SOURCE_DB}?mode=ro",
        uri=True,
    )
    source.row_factory = sqlite3.Row

    # ------------------------------------------------------------
    # Connect to PostgreSQL
    # ------------------------------------------------------------

    target_engine = create_engine(
        target_url,
        pool_pre_ping=True,
    )

    print("Testing PostgreSQL connection...")

    with target_engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    print("PostgreSQL connection: OK")

    # ------------------------------------------------------------
    # Create tables if they do not exist
    # ------------------------------------------------------------

    print()
    print("Ensuring PostgreSQL tables exist...")

    Base.metadata.create_all(bind=target_engine)

    # ------------------------------------------------------------
    # SAFETY CHECK
    #
    # Refuse to migrate if target already contains data.
    # This prevents accidental duplicate/overwrite operations.
    # ------------------------------------------------------------

    with target_engine.connect() as connection:
        target_users = connection.execute(
            text("SELECT COUNT(*) FROM users")
        ).scalar_one()

        target_works = connection.execute(
            text("SELECT COUNT(*) FROM works")
        ).scalar_one()

        target_similarities = connection.execute(
            text("SELECT COUNT(*) FROM work_similarities")
        ).scalar_one()

    print()
    print("Current PostgreSQL counts:")
    print("Users:", target_users)
    print("Works:", target_works)
    print("Similarities:", target_similarities)

    if target_users != 0 or target_works != 0 or target_similarities != 0:
        raise RuntimeError(
            "SAFETY STOP: PostgreSQL database is not empty. "
            "No migration was performed."
        )

    # ------------------------------------------------------------
    # Verify source counts
    # ------------------------------------------------------------

    source_users = source.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    source_works = source.execute(
        "SELECT COUNT(*) FROM works"
    ).fetchone()[0]

    source_similarities = source.execute(
        "SELECT COUNT(*) FROM work_similarities"
    ).fetchone()[0]

    print()
    print("Source SQLite counts:")
    print("Users:", source_users)
    print("Works:", source_works)
    print("Similarities:", source_similarities)

    if source_users != EXPECTED_USERS:
        raise RuntimeError(
            f"Unexpected user count: {source_users}. "
            f"Expected {EXPECTED_USERS}."
        )

    if source_works != EXPECTED_WORKS:
        raise RuntimeError(
            f"Unexpected works count: {source_works}. "
            f"Expected {EXPECTED_WORKS}."
        )

    if source_similarities != EXPECTED_SIMILARITIES:
        raise RuntimeError(
            f"Unexpected similarity count: {source_similarities}. "
            f"Expected {EXPECTED_SIMILARITIES}."
        )

    print()
    print("Source verification: PASSED")

    # ------------------------------------------------------------
    # Read source column names
    # ------------------------------------------------------------

    user_columns = get_sqlite_columns(source, "users")
    work_columns = get_sqlite_columns(source, "works")
    similarity_columns = get_sqlite_columns(
        source,
        "work_similarities",
    )

    # ------------------------------------------------------------
    # Target columns from SQLAlchemy models
    # ------------------------------------------------------------

    user_target_columns = [
        column.name for column in User.__table__.columns
    ]

    work_target_columns = [
        column.name for column in Work.__table__.columns
    ]

    similarity_target_columns = [
        column.name for column in WorkSimilarity.__table__.columns
    ]

    user_insert_columns = [
        column
        for column in user_target_columns
        if column in user_columns
    ]

    work_insert_columns = [
        column
        for column in work_target_columns
        if column in work_columns
    ]

    similarity_insert_columns = [
        column
        for column in similarity_target_columns
        if column in similarity_columns
    ]

    # ------------------------------------------------------------
    # Migration
    # ------------------------------------------------------------

    print()
    print("Starting migration...")
    print("SQLite database will remain READ-ONLY.")

    with target_engine.begin() as connection:

        # --------------------------------------------------------
        # USERS
        # --------------------------------------------------------

        print()
        print("Migrating users...")

        user_rows = source.execute(
            "SELECT * FROM users"
        ).fetchall()

        user_payload = []

        for row in user_rows:
            item = {}

            for column in user_insert_columns:
                value = row[column]

                if column == "created_at":
                    value = parse_datetime(value)

                item[column] = value

            user_payload.append(item)

        if user_payload:
            connection.execute(
                User.__table__.insert(),
                user_payload,
            )

        print(f"Users migrated: {len(user_payload)}")

        # --------------------------------------------------------
        # WORKS
        # --------------------------------------------------------

        print()
        print("Migrating works...")

        work_cursor = source.execute(
            "SELECT * FROM works"
        )

        batch = []
        migrated_works = 0
        batch_size = 1000

        while True:
            rows = work_cursor.fetchmany(batch_size)

            if not rows:
                break

            for row in rows:
                item = {}

                for column in work_insert_columns:
                    value = row[column]

                    if column in {
                        "created_at",
                        "updated_at",
                        "risk_computed_at",
                    }:
                        value = parse_datetime(value)

                    item[column] = value

                batch.append(item)

            if len(batch) >= batch_size:
                connection.execute(
                    Work.__table__.insert(),
                    batch,
                )

                migrated_works += len(batch)
                print(
                    f"Works migrated: {migrated_works}/{source_works}"
                )

                batch.clear()

        if batch:
            connection.execute(
                Work.__table__.insert(),
                batch,
            )

            migrated_works += len(batch)
            print(
                f"Works migrated: {migrated_works}/{source_works}"
            )

            batch.clear()

        # --------------------------------------------------------
        # SIMILARITIES
        # --------------------------------------------------------

        print()
        print("Migrating work similarities...")

        similarity_cursor = source.execute(
            "SELECT * FROM work_similarities"
        )

        batch = []
        migrated_similarities = 0
        batch_size = 2000

        while True:
            rows = similarity_cursor.fetchmany(batch_size)

            if not rows:
                break

            for row in rows:
                item = {}

                for column in similarity_insert_columns:
                    item[column] = row[column]

                batch.append(item)

            if len(batch) >= batch_size:
                connection.execute(
                    WorkSimilarity.__table__.insert(),
                    batch,
                )

                migrated_similarities += len(batch)
                print(
                    "Similarities migrated: "
                    f"{migrated_similarities}/{source_similarities}"
                )

                batch.clear()

        if batch:
            connection.execute(
                WorkSimilarity.__table__.insert(),
                batch,
            )

            migrated_similarities += len(batch)
            print(
                "Similarities migrated: "
                f"{migrated_similarities}/{source_similarities}"
            )

            batch.clear()

    # ------------------------------------------------------------
    # PostgreSQL validation
    # ------------------------------------------------------------

    print()
    print("=" * 70)
    print("POSTGRESQL VALIDATION")
    print("=" * 70)

    with target_engine.connect() as connection:

        users = connection.execute(
            text("SELECT COUNT(*) FROM users")
        ).scalar_one()

        works = connection.execute(
            text("SELECT COUNT(*) FROM works")
        ).scalar_one()

        similarities = connection.execute(
            text("SELECT COUNT(*) FROM work_similarities")
        ).scalar_one()

        high = connection.execute(
            text(
                "SELECT COUNT(*) FROM works "
                "WHERE risk_level = 'High'"
            )
        ).scalar_one()

        medium = connection.execute(
            text(
                "SELECT COUNT(*) FROM works "
                "WHERE risk_level = 'Medium'"
            )
        ).scalar_one()

        low = connection.execute(
            text(
                "SELECT COUNT(*) FROM works "
                "WHERE risk_level = 'Low'"
            )
        ).scalar_one()

    print("Users:", users)
    print("Works:", works)
    print("Similarities:", similarities)
    print("High:", high)
    print("Medium:", medium)
    print("Low:", low)

    if users != EXPECTED_USERS:
        raise RuntimeError("PostgreSQL user count validation failed.")

    if works != EXPECTED_WORKS:
        raise RuntimeError("PostgreSQL works count validation failed.")

    if similarities != EXPECTED_SIMILARITIES:
        raise RuntimeError(
            "PostgreSQL similarity count validation failed."
        )

    if high != 381:
        raise RuntimeError("PostgreSQL HIGH count validation failed.")

    if medium != 7780:
        raise RuntimeError("PostgreSQL MEDIUM count validation failed.")

    if low != 30105:
        raise RuntimeError("PostgreSQL LOW count validation failed.")

    print()
    print("SUCCESS: PostgreSQL migration validated.")
    print()
    print("SQLite source database was not modified.")
    print("=" * 70)


if __name__ == "__main__":
    main()