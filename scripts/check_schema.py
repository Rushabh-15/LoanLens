"""
Compare the database's tables with the ORM models and report drift.

create_all() creates missing tables but never changes existing ones, so a
model change (such as B2's reason_codes column) can leave an old local
database behind. Run this from the project root after changing
app/models/db_models.py:

    python -m scripts.check_schema

Exit code 0 means the database matches the models; 1 means it does not.
"""

import sys

from sqlalchemy import Engine, inspect

from app.db import Base, engine
from app.models import db_models  # noqa: F401  (imports the models so Base knows the tables)


def find_drift(target: Engine) -> list[str]:
    """Return one line per difference between the models and the database."""
    inspector = inspect(target)
    existing_tables = set(inspector.get_table_names())
    problems = []

    for table in Base.metadata.sorted_tables:
        # A missing table is not drift: create_all() makes it on startup.
        if table.name not in existing_tables:
            continue

        db_columns = {column["name"] for column in inspector.get_columns(table.name)}
        model_columns = {column.name for column in table.columns}

        for name in sorted(model_columns - db_columns):
            problems.append(f"{table.name}.{name}: in the model, missing from the database")

        for name in sorted(db_columns - model_columns):
            problems.append(f"{table.name}.{name}: in the database, not in the model")

    return problems


def main() -> int:
    print(f"Database: {engine.url.render_as_string(hide_password=True)}")

    problems = find_drift(engine)

    if not problems:
        print("Schema matches the models.")
        return 0

    print("Schema drift found:")
    for problem in problems:
        print(f"  - {problem}")
    print(
        "Recreate the development database (see docs/DECISIONS.md) "
        "or write a migration."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())