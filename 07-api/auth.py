"""Basic authentication concept (PLAN.md §22, security-model.md's role table).

Every request must carry a matching X-API-Key header. This is deliberately
the simplest thing that demonstrates the concept -- a single shared key,
no per-user identity, no roles, no expiry -- because this project's
security-model.md is explicit that a full identity/role system is out of
scope for a portfolio POC. Phase 12's AI safety policy and Phase 11's
approval workflow are where role-aware access actually matters; this layer
just proves the API isn't wide open.
"""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from config import API_SECRET_KEY


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid X-API-Key header")
