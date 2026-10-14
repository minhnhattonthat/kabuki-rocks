"""One-command check (the pre-commit hook runs this): every test under tests/, then the text lint."""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
py = [sys.executable, "-X", "utf8"]
rc = subprocess.call(py + ["-m", "pytest", "-q", str(ROOT / "tests")], cwd=ROOT)
rc = subprocess.call(py + [str(ROOT / "tools" / "lint.py")], cwd=ROOT) or rc
sys.exit(rc)
