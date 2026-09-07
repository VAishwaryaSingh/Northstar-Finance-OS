"""Makes the 06-python/ modules importable from the tests/ subfolder.

06-python is not a valid Python package name (it starts with a digit and
contains a hyphen), so these modules are imported as plain top-level
modules (import mappings, import validation, ...) with this directory
added to sys.path, rather than via a package-relative import.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
