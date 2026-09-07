# ADR-0004: Retain the legacy ERP initially rather than a big-bang cutover

## Context

Northstar Health Group's current-state environment ([current-state.md](../02-process-mapping/current-state.md)) runs on a legacy per-entity ERP with inconsistent chart-of-accounts setup (R07) and no single master-data source (R09). The target architecture needs to decide whether the legacy ERP is replaced immediately or coexists with the new finance data model during a transition period.

## Options considered

- **Big-bang cutover** — decommission the legacy ERP and migrate everything to the new data model in one step; architecturally simpler, but unrealistic for any real multi-entity close process and inconsistent with the phased migration approach PLAN.md §29 already calls for (inventory → mapping → cleansing → validation → cutover)
- **Retain the legacy ERP as a read-only source during transition** — the legacy ERP continues operating and is ingested into the new architecture as one of the four sources ([integration-map.md](../03-architecture/integration-map.md)), with its data mapped into the single chart of accounts on the way in, until migration is complete

## Decision

Retain the legacy ERP as a read-only source feeding the Integration layer during the transition period, rather than assuming an immediate replacement. It is treated the same as Billing/Banking/AP: ingested, validated, and mapped into the single entity-aware data model — not migrated wholesale in one step.

## Trade-offs

- Running the legacy ERP alongside the new architecture for a transition period means temporarily maintaining two systems' worth of process, which is more operational overhead than a clean cutover
- This is the only realistic option for a multi-entity close process where a single-day cutover would create close-cycle risk exactly where the project is trying to reduce it (R01)

## Consequences

- Legacy ERP is documented as a standing source in [integration-map.md](../03-architecture/integration-map.md), not a one-time migration job
- `12-implementation/migration-plan.md` (Phase 15, PLAN.md §29) builds on this decision — the migration plan assumes phased cutover, not a big-bang replacement
