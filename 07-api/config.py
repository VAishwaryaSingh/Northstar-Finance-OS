"""API configuration.

API_SECRET_KEY is the bearer value clients must send in the X-API-Key
header (see auth.py) -- a basic authentication *concept* per PLAN.md §22
and security-model.md, not a production auth system: no user accounts,
no token expiry, no scopes. Read from the environment / .env, per
.env.example, with a clearly-fake local-dev fallback so the API is
runnable out of the box without requiring secrets to be configured first.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

API_SECRET_KEY = os.environ.get("API_SECRET_KEY", "local-dev-placeholder-key")
