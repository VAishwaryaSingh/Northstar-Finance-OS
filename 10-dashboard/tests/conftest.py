"""Makes the 10-dashboard/ modules importable from tests/ -- same fix as
every other phase's tests/conftest.py in this project."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
