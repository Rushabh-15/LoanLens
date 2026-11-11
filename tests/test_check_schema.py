from sqlalchemy import create_engine, text

from app.db import Base
from scripts.check_schema import find_drift


# The applications table as it was before B2 added reason_codes.
PRE_B2_TABLE = """
CREATE TABLE applications (
    id INTEGER NOT NULL PRIMARY KEY,
    extracted_fields JSON NOT NULL,
    emi FLOAT NOT NULL,
    foir FLOAT NOT NULL,
    risk_flags JSON NOT NULL,
    decision VARCHAR NOT NULL,
    reason VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
)
"""


def test_fresh_database_has_no_drift(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    Base.metadata.create_all(engine)

    assert find_drift(engine) == []


def test_pre_b2_database_reports_the_missing_column(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as connection:
        connection.execute(text(PRE_B2_TABLE))

    assert find_drift(engine) == [
        "applications.reason_codes: in the model, missing from the database"
    ]


def test_empty_database_is_not_drift(tmp_path):
    # create_all() will make the table on startup, so nothing is wrong yet.
    engine = create_engine(f"sqlite:///{tmp_path / 'empty.db'}")

    assert find_drift(engine) == []


def test_extra_database_column_is_reported(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'extra.db'}")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE applications ADD COLUMN legacy_note TEXT"))

    assert find_drift(engine) == [
        "applications.legacy_note: in the database, not in the model"
    ]