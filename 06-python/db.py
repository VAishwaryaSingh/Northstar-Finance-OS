"""Database connection helper.

Reads DATABASE_URL from the environment (via a local .env file if present,
per .env.example) and falls back to the local peer-auth connection used for
development on this machine, where PostgreSQL trusts the OS user with no
password needed.
"""

from __future__ import annotations

import getpass
import os

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine

load_dotenv()

# No TCP host in the connection string -> connects over the local unix
# socket using peer auth (same as running `psql -d northstar` with no -h),
# which is how this machine's PostgreSQL install is configured -- no
# password. Peer auth maps the OS user to a same-named DB role, so this
# only works when run as the OS user that owns the northstar database
# (see 05-sql/README.md's local setup instructions).
DEFAULT_LOCAL_URL = f"postgresql+psycopg2://{getpass.getuser()}@/northstar?host=/var/run/postgresql"


def get_engine() -> Engine:
    url = os.environ.get("DATABASE_URL", DEFAULT_LOCAL_URL)
    return create_engine(url)
