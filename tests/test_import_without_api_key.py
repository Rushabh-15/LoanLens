import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_app_imports_without_anthropic_api_key(tmp_path):
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    env["PYTHON_DOTENV_DISABLED"] = "1"

    # Isolate any import-time database access.
    # Assumes app.db reads its connection URL from DATABASE_URL.
    env["DATABASE_URL"] = f"sqlite:///{tmp_path / 'import_test.db'}"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import os\n"
                "assert 'ANTHROPIC_API_KEY' not in os.environ\n"
                "import app.main\n"
                "assert 'ANTHROPIC_API_KEY' not in os.environ\n"
            ),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, (
        "Importing app.main without ANTHROPIC_API_KEY failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )