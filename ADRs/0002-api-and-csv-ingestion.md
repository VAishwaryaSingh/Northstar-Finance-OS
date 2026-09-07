# ADR-0002: API ingestion where available, CSV ingestion everywhere else

## Context

Four sources feed the Integration layer ([integration-map.md](../03-architecture/integration-map.md)): Billing, Banking, AP, and the legacy ERP. They don't all offer the same connectivity — billing platforms commonly expose an API; bank feeds and AP systems in a mid-market multi-entity environment are frequently file-export only; the legacy ERP is being phased out, not integrated with long-term.

## Options considered

- **API-only integration** — cleanest architecture on paper, but unrealistic: not every source in this environment actually has an API to call
- **CSV-only integration** — works everywhere but throws away real-time capability where it does exist (billing), and undersells the API design skill this project is meant to demonstrate (PLAN.md §22 requires a REST API layer regardless)
- **API where available, structured file (CSV) ingestion as the standard fallback** — matches what sources actually support

## Decision

Use API ingestion for sources that support it (billing, per R03) and CSV ingestion as the standard path for everything else (banking, AP, legacy ERP). Both paths converge on the same validation and transformation logic in the Integration layer — the ingestion method is a connector detail, not a difference in what gets validated.

## Trade-offs

- Running two ingestion mechanisms is more to build than one, but reflects the real heterogeneity of source systems rather than an artificially simplified integration story
- CSV ingestion is inherently batch (daily), so billing data arriving via CSV fallback loses near-real-time capability — acceptable since the API path is the primary route for billing

## Consequences

- `06-python/ingestion.py` (Phase 9) needs both an API client path and a file-read path, both feeding the same validation/transformation pipeline
- Every source's actual connection detail (direction, format, frequency, failure handling) is documented per-source in [integration-map.md](../03-architecture/integration-map.md)
