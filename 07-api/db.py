"""Database connection helper -- same approach as 06-python/db.py.

07-api and 06-python each keep their own copy rather than sharing one
module: neither directory is a valid Python package name (both start with
a digit), so importing across them would need path hacks on top of path
hacks. A five-line file duplicated twice is simpler than that.
"""

from __future__ import annotations

import getpass
import os

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine

load_dotenv()

DEFAULT_LOCAL_URL = f"postgresql+psycopg2://{getpass.getuser()}@/northstar?host=/var/run/postgresql"

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = os.environ.get("DATABASE_URL", DEFAULT_LOCAL_URL)
        _engine = create_engine(url)
    return _engine
