# Integration Map — Northstar Finance OS

How each source system in [system-architecture.md](./system-architecture.md) actually connects into the Integration layer. Complements that document by going one level deeper on each connection: direction, format, frequency, validation, and failure handling.

| Source | Direction | Format | Frequency | Validation on arrival | Failure handling |
|---|---|---|---|---|---|
| Billing | Inbound (pull) | API (JSON) where available; CSV export as fallback | Near-real-time via API; daily batch if using file fallback | Schema validation, duplicate-invoice detection, entity code presence | Rejected records routed to exception queue with reason code — never dropped, never silently retried into a duplicate |
| Banking | Inbound (pull/import) | CSV — standard bank statement export format | Daily batch | Schema validation, currency/entity mapping check | Unmatched or malformed rows routed to exception queue for reconciliation review |
| AP | Inbound (import) | CSV — vendor invoice export | Daily batch | Schema validation, duplicate-invoice detection, vendor mapping check | Duplicate or unmapped invoices held in exception queue before payment run (this is the fix for R10 — duplicates must be caught before payment, not after) |
| Legacy ERP | Inbound (read-only import), retained during transition — see [ADR-0004](../ADRs/0004-retain-legacy-erp-initially.md) | CSV export | Daily batch, until migration cutover (Phase 6 onward) | Schema validation, entity/CoA mapping check against the single mapped chart of accounts | Unmappable legacy entries flagged for manual mapping review, not auto-mapped |

## Why API where available, CSV everywhere else

Billing is the only source realistically offering an API in this environment; banking, AP, and the legacy ERP are treated as file-based integrations. Standardising on file ingestion as the baseline (with API as an upgrade path per source, not a hard requirement) keeps the integration layer usable regardless of what each source system actually supports. Full reasoning: [ADR-0002](../ADRs/0002-api-and-csv-ingestion.md).

## Common validation applied to every source

Regardless of source, everything passes through the same Integration-layer checks before it reaches the Finance Data Model (PLAN.md §21 ingestion pipeline, built in Phase 9):

1. Schema validation — required fields present, types correct
2. Duplicate detection — R10
3. Entity/account mapping — against the single chart of accounts, R07/R09
4. Currency normalisation — R08

Anything that fails any of these steps is routed to an exception queue (Controls layer), never dropped and never posted unvalidated. This single validation point is the future-state fix for the current-state pattern documented in [process-analysis.md](../02-process-mapping/process-analysis.md): "validation and matching logic exist only in people's heads and spreadsheets, applied downstream and inconsistently."

## Out of scope for this phase

This document describes the target integration pattern, not the implementation. Actual connector code, API client details, and file-watch/scheduling mechanics are built in Phase 9 (`06-python/`, PLAN.md §21).
