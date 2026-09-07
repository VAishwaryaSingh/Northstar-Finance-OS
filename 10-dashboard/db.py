"""Database connection helper -- same approach as every other phase's
db.py (see 07-api/db.py's docstring for why each phase keeps its own tiny
copy rather than sharing one module across directories that aren't valid
Python package names)."""

from __future__ import annotations

import getpass
import os

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine

load_dotenv()

DEFAULT_LOCAL_URL = f"postgresql+psycopg2://{getpass.getuser()}@/northstar?host=/var/run/postgresql"


def get_engine() -> Engine:
    url = os.environ.get("DATABASE_URL", DEFAULT_LOCAL_URL)
    return create_engine(url)
