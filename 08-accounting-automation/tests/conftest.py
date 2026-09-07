"""Makes the 08-accounting-automation/ modules importable from tests/ --
same fix as 06-python/tests/conftest.py and 07-api/tests/conftest.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
