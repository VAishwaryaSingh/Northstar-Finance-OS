# REST API — Northstar Finance OS

FastAPI implementation of PLAN.md §22's "ERP-style integration surface" — the layer that lets another system (or, later, the dashboard in Phase 14) talk to the finance data model over HTTP instead of SQL.

## Run it

```bash
.venv/bin/uvicorn main:app --reload --app-dir 07-api
```

Then visit `http://127.0.0.1:8000/docs` for FastAPI's auto-generated Swagger UI, or call it directly:

```bash
curl -X POST http://127.0.0.1:8000/customers \
  -H "X-API-Key: local-dev-placeholder-key" -H "Content-Type: application/json" \
  -d '{"customer_code":"C9001","customer_name":"Test Customer Ltd","entity_code":"NHH-UK","billing_currency":"GBP"}'
```

Needs the `northstar` PostgreSQL database from Phase 8 (`05-sql/README.md`) with the Phase 9 pipeline's data loaded.

## Endpoints (PLAN.md §22)

| Endpoint | Notes |
|---|---|
| `POST /customers` | |
| `POST /invoices` | **Idempotent** on `(entity_code, invoice_number, invoice_type)` — see below |
| `POST /payments` | `invoice_id` is optional (unapplied cash) |
| `POST /journal-entries` | Balance and maker≠checker validated client-side (422) *and* by schema.sql's trigger/constraint (400) — see "Two layers of the same rule" below |
| `GET /trial-balance` | optional `?entity_code=` |
| `GET /reconciliation-status` | optional `?entity_code=` |
| `GET /close-status` | optional `?entity_code=&period=` |
| `GET /intercompany-exceptions` | optional `?entity_code=` |
| `GET /health` | unauthenticated liveness check |

All endpoints except `/health` require an `X-API-Key` header (see "Authentication" below).

## What each PLAN.md §22 requirement looks like here

- **Request validation** — Pydantic models in `schemas.py`: known currency codes, positive amounts, an AR invoice must carry a customer code (an AP one a vendor code), a journal entry needs ≥2 lines each with exactly one of debit/credit set.
- **Response schemas** — every endpoint declares a `response_model`; FastAPI enforces the shape of what goes out, not just what comes in.
- **Errors + HTTP status codes** — `errors.py`'s `NotFoundError`/`BusinessRuleError`, plus SQLAlchemy's `IntegrityError`, are mapped to clean JSON responses by exception handlers in `main.py` (404, 400, 400) rather than leaking a stack trace or raw SQL error.
- **Basic authentication concept** — a single shared `X-API-Key` header, checked in `auth.py`. This is deliberately not a real auth system (no accounts, no roles, no expiry) — see `03-architecture/security-model.md`'s stated limitations, which this matches on purpose.
- **Idempotency** — `POST /invoices` (see below).
- **Logging** — a middleware in `main.py` logs method, path, status code, and duration for every request.

## Idempotent invoice creation

`POST /invoices` treats `(entity_code, invoice_number, invoice_type)` as the natural key a real client would retry against:

| Situation | Response |
|---|---|
| No existing invoice with that key | **201** — new invoice, `status: "open"` |
| Existing invoice, same amount | **200** — the *existing* invoice is returned, `idempotent_replay: true`. Nothing new is created — this is what makes a retried request safe. |
| Existing invoice, different amount | **201** — a genuinely new row is inserted, but `status: "duplicate_flagged"` rather than `"open"`. This is R10's actual requirement (flagged before payment, not after), reusing the same idea as `06-python/reconciliation.py`'s duplicate flagging. |

## Two layers of the same accounting rule

`POST /journal-entries` validates balance (`Σdebits = Σcredits`) and maker≠checker in `schemas.py` *before* touching the database — a client gets a clean, immediate `422` with a readable message. `05-sql/schema.sql`'s deferred trigger and `CHECK` constraint enforce the exact same two rules again, at the database level, as the actual source of truth — so even a request that somehow bypassed this API (a script writing SQL directly, a bug in the client-side check) still can't produce a bad journal entry. `main.py`'s `IntegrityError` handler is what a client would see if that second layer is what caught it (a `400`, not a raw database error).

## Tests

```bash
.venv/bin/pytest 07-api/tests -v
```

27 tests, run against the real database (no mocking) via FastAPI's `TestClient`. Each test that needs to create data gets its own throwaway entity (`test_entity` fixture in `conftest.py`) so nothing touches the Phase 7/8/9 seeded dataset, and it's deleted again at teardown.

## Known limitations

- Authentication is a single shared key, not per-user identity or roles — matches `security-model.md`'s explicitly stated scope for this portfolio project, not a gap to silently work around.
- No pagination on the `GET` endpoints — fine at this dataset's size (a few hundred rows), would need addressing before this scaled up.
- `POST /invoices` and `POST /payments` don't yet call into `06-python`'s fuzzy vendor-name matching — an API caller is expected to send a `vendor_code` that already exists, the same way a real integration partner would send a code it already has on file, not free-text needing to be guessed at.
