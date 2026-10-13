import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


# Stop if the database engine was initialized before this configuration.
if "app.db" in sys.modules:
    raise RuntimeError(
        "app.db was imported before the test database was configured. "
        "Run pytest with the tests directory selected."
    )


# Keep this object alive for the entire pytest run.
_TEST_DIRECTORY = TemporaryDirectory(prefix="loanlens-tests-")
_TEST_DATABASE_PATH = (
    Path(_TEST_DIRECTORY.name).resolve() / "test.db"
)

# Always override any development database URL inherited from the shell.
# This must happen before importing any application modules.
os.environ["DATABASE_URL"] = (
    f"sqlite:///{_TEST_DATABASE_PATH.as_posix()}"
)


def pytest_unconfigure(config):
    """Close database connections and remove the temporary directory."""
    db_module = sys.modules.get("app.db")

    try:
        if db_module is not None:
            db_module.engine.dispose()
    finally:
        _TEST_DIRECTORY.cleanup()