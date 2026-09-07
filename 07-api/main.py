"""Northstar Finance OS — REST API (PLAN.md §22).

The ERP-style integration surface sitting on top of the schema built in
Phase 8 and loaded by the pipeline built in Phase 9. Demonstrates request
validation, response schemas, structured error handling with real HTTP
status codes, a basic authentication concept, idempotent invoice
creation, and request logging -- the six things PLAN.md §22 asks this
phase to show.

Run: .venv/bin/uvicorn main:app --reload --app-dir 07-api
Docs: http://127.0.0.1:8000/docs (FastAPI's auto-generated Swagger UI)
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

# Ensures sibling modules (db, models, schemas, routes/...) import cleanly
# regardless of how uvicorn/pytest was launched -- 07-api isn't a valid
# Python package name (leading digit), so it can never be imported as one;
# this is the same fix as 06-python/tests/conftest.py, just applied here
# so it works no matter which module gets imported first.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from errors import BusinessRuleError, NotFoundError  # noqa: E402
from routes import customers, invoices, journal_entries, payments, reporting  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("northstar-api")

app = FastAPI(
    title="Northstar Finance OS API",
    description="Fictional portfolio ERP integration surface -- see PLAN.md and AGENTS.md.",
    version="0.1.0",
)

app.include_router(customers.router)
app.include_router(invoices.router)
app.include_router(payments.router)
app.include_router(journal_entries.router)
app.include_router(reporting.router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = round((time.monotonic() - start) * 1000, 1)
    logger.info(f'{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)')
    return response


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(BusinessRuleError)
async def business_rule_handler(request: Request, exc: BusinessRuleError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    # A database constraint (debit=credit, maker!=checker, ...) rejected
    # the request. Logged in full for debugging; the client only sees a
    # generic message, never the raw SQL/driver error.
    logger.warning(f"database constraint violation: {exc}")
    return JSONResponse(status_code=400, content={"detail": "request violates a database accounting constraint"})


@app.get("/health")
def health():
    return {"status": "ok"}
