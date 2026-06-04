import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def test_main_module_is_importable():
    result = subprocess.run(
        [sys.executable, "-m", "src", "--help"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0
    assert "BIND" in result.stdout or "Usage" in result.stdout
