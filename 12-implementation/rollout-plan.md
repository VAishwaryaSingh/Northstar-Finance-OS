# Rollout Plan — Northstar Finance OS

Implementation Plan Phases 7-8 in detail: which entity pilots first, why, and how the remaining two entities follow.

## Pilot entity: Northstar Shared Services Ltd (UK)

**Assumption, stated explicitly:** this project has no real per-entity transaction volume or complexity data to rank the three entities by — [discovery-notes.md](../01-discovery/discovery-notes.md) gives group-level figures only (~5,000 transactions/month, 12-day close). The selection below is a reasoned assumption a real engagement would confirm with the Controller in Implementation Plan Phase 0, not a measured fact.

Reasoning:
- **GBP-only** — no FX conversion risk during the pilot itself ([requires_fx_conversion](../08-accounting-automation/invoice_classification.py) still applies to any intercompany transaction touching the US entity, but the pilot entity's own transactions carry no currency-translation risk)
- **The Shared Services team already operates this entity directly** — per [current-state.md](../02-process-mapping/current-state.md), Shared Services runs the billing export, re-keying, and bank reconciliation steps today. Piloting on their own entity means the team learning the new system is the same team that will use it group-wide, with the shortest possible feedback loop
- **Not the intercompany hub** — piloting on an entity with fewer intercompany relationships limits how far a pilot-period issue can propagate into entities not yet on the new system

## Phased schedule

| Stage | Entity/scope | Duration | Gate to proceed |
|---|---|---|---|
| Pilot | Northstar Shared Services Ltd (UK) — one full close cycle | 4-6 weeks | [Validation](./migration-plan.md#validation) passes; UAT sign-off from the Controller; no unresolved P0 defect |
| Rollout 1 | + Northstar Health Holdings Ltd (UK) | 2-3 weeks | Pilot close completed cleanly at least once; pilot-specific defects resolved |
| Rollout 2 | + Northstar Health Services Inc (US) — full group live | 3-4 weeks | Both UK entities stable for ≥1 close cycle; FX/cross-border controls ([requires_fx_conversion](../08-accounting-automation/invoice_classification.py)) specifically re-verified, since this is the first entity to actually exercise them for its own (not just intercompany) transactions |

Total rollout: **9-13 weeks**, consistent with the 4-8 week Phase 8 estimate in [implementation-plan.md](./implementation-plan.md) plus the pilot itself.

## Cutover approach

Per [ADR-0004](../ADRs/0004-retain-legacy-erp-initially.md): **no big-bang cutover.** For each entity, at the point it rolls onto the new system:

1. Legacy ERP for that entity moves to read-only (still queryable for history, no new postings)
2. New transactions from cutover date forward post through [07-api](../07-api/) / [06-python](../06-python/) ingestion, governed by [08-accounting-automation](../08-accounting-automation/)'s rules from day one — not phased in gradually, since a control that's "mostly on" isn't a control
3. Legacy and new systems run in parallel for one full close cycle per entity, with [Validation](./migration-plan.md#validation) run against both to confirm they agree before the legacy system for that entity is formally retired

## Rollback / contingency

- **Per-entity, not group-wide** — because rollout is staged by entity, a serious issue discovered during, say, the second UK entity's rollout doesn't require rolling back the pilot entity, which has already had a full close cycle validated
- **Legacy ERP stays available (read-only, per cutover approach above) through at least one full close cycle post-cutover** for every entity — the fallback is "revert that entity's new-transaction posting to the legacy system and re-extract," not a from-scratch data recovery
- **Trigger for rollback:** any control failure that would let an entry post without required approval or unbalanced (should be structurally impossible per [schema.sql](../05-sql/schema.sql)'s constraints, but "should be impossible" is exactly the class of assumption a rollback trigger needs to cover, not exempt)

See [risks.md](./risks.md) for the full risk register behind these decisions, and [training-plan.md](./training-plan.md) for how each stage's users are prepared before their entity goes live.
