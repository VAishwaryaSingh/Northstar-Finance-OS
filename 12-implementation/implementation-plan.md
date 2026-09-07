# Implementation Plan — Northstar Finance OS

The 9-phase structure PLAN.md §28 specifies, made concrete against Northstar Health Group's actual current-state ([current-state.md](../02-process-mapping/current-state.md)) and this project's real deliverables. Where a phase's output already exists in this repository, it's linked directly — this plan isn't hypothetical about the parts already built; it's honest about what's still notional for an actual deployment (the pilot and rollout phases, since there's no real second environment or real users here).

## Timeline overview

| Phase | Duration (est.) | Status in this POC |
|---|---|---|
| 0 — Discovery | 1-2 weeks | **Done** — [01-discovery/](../01-discovery/) |
| 1 — Design | 1-2 weeks | **Done** — [03-architecture/](../03-architecture/), [ADRs/](../ADRs/) |
| 2 — Data preparation | 2-3 weeks | **Done, on synthetic data** — [04-data/](../04-data/); real legacy extract/cleanse is Migration Plan's job |
| 3 — Integration | 2-4 weeks | **Done** — [06-python/](../06-python/), [07-api/](../07-api/) |
| 4 — Configuration | 1 week | **Done** — [05-sql/schema.sql](../05-sql/schema.sql), [08-accounting-automation/](../08-accounting-automation/) |
| 5 — Testing | 2-3 weeks | **Done, continuously** — 128 automated tests across every phase, run against real data at every step |
| 6 — Migration | 2-3 weeks | Notional — see [migration-plan.md](./migration-plan.md) |
| 7 — Pilot | 4-6 weeks | Notional — see [rollout-plan.md](./rollout-plan.md) |
| 8 — Rollout | 4-8 weeks | Notional — see [rollout-plan.md](./rollout-plan.md) |

**~19-32 weeks (roughly 4.5-8 months) end to end** for a real deployment at Northstar Health Group's actual scale (3 entities, ~5,000 transactions/month — AGENTS.md). This project compressed Phases 0-5 into a single continuous build specifically to demonstrate every phase's actual deliverable, not to claim a real deployment would move this fast.

## Phase 0 — Discovery

**Stakeholders:** CFO, Group Financial Controller, Shared Services Manager (the three discovery personas in [discovery-notes.md](../01-discovery/discovery-notes.md)), plus — for a real engagement — IT/systems owner and external auditors (control design needs their early input, not a post-hoc review).

**Processes:** the current-state close, AP, bank reconciliation, and intercompany process, mapped in [current-state.md](../02-process-mapping/current-state.md).

**Systems:** legacy per-entity ERP, billing platform, online banking export — [system-architecture.md](../03-architecture/system-architecture.md)'s Sources layer.

**Requirements:** [requirements.md](../01-discovery/requirements.md)'s R01-R12, each with a success metric, not just a description.

## Phase 1 — Design

**Architecture:** [system-architecture.md](../03-architecture/system-architecture.md) — Sources → Integration → Core → AI → Controls → Outputs.

**Data model:** [data-model.md](../03-architecture/data-model.md) — 14 tables, debit=credit and maker≠checker enforced at the schema level, not just documented.

**Controls:** [security-model.md](../03-architecture/security-model.md) plus every phase's own `controls.md`.

**Integration design:** [integration-map.md](../03-architecture/integration-map.md) — API where available (billing), file-based everywhere else.

## Phase 2 — Data preparation

In this POC: [04-data/generate_data.py](../04-data/generate_data.py) generates synthetic source data deliberately containing the same messiness a real legacy extract would (duplicates, missing codes, inconsistent vendor names — [data-quality-log.md](../04-data/data-quality-log.md)).

For a real deployment, this phase is where [migration-plan.md](./migration-plan.md)'s data inventory, mapping, and cleansing actually happen against real legacy data — this POC's synthetic messiness stands in for that work, not replaces it.

## Phase 3 — Integration

**API:** [07-api/](../07-api/) — the ERP-style integration surface (customers, invoices, payments, journal entries, reporting endpoints).

**Files:** [06-python/ingestion.py](../06-python/ingestion.py) — schema validation, data-quality checks, duplicate detection, entity/account mapping, currency normalisation.

**Banking:** bank statement ingestion, matched via [06-python/reconciliation_engine.py](../06-python/reconciliation_engine.py).

**Billing:** the one source with a real API path per [ADR-0002](../ADRs/0002-api-and-csv-ingestion.md).

## Phase 4 — Configuration

**Chart of accounts:** single shared CoA, [schema.sql](../05-sql/schema.sql)'s `chart_of_accounts` table — this is itself the fix for R07 (today's per-entity CoA drift).

**Entities:** the three Northstar entities, `entities` table.

**Approval rules:** [journal_workflow.py](../08-accounting-automation/journal_workflow.py)'s threshold (still a placeholder assumption — see that module's `controls.md` — a real deployment confirms the actual figure with the Controller here, in Phase 4, before go-live).

**Accounting rules:** [invoice_classification.py](../08-accounting-automation/invoice_classification.py), [exception_rules.py](../08-accounting-automation/exception_rules.py) — vendor→account mapping, duplicate detection, amount-outlier detection, audit sampling.

## Phase 5 — Testing

**Unit testing:** 128 pytest tests across every module, run continuously as each phase was built, not saved for a single testing phase at the end.

**Integration testing:** [07-api/tests/](../07-api/tests/) exercises the full request→database→response path against the real database via FastAPI's `TestClient`.

**Reconciliation testing:** [06-python/tests/test_reconciliation_engine.py](../06-python/tests/test_reconciliation_engine.py) plus [run_reconciliation.py](../06-python/run_reconciliation.py)'s real-data proof run.

**UAT:** notional for this POC (no real users) — for an actual deployment, this is where the CFO/Controller personas from Discovery actually use the [Close Control Centre dashboard](../10-dashboard/) against a parallel-run period before go-live.

**Controls testing:** every `controls.md` across Phases 5, 11, and 12 documents which control maps to which test — including [09-ai/tests/](../09-ai/tests/)'s deliberate attempts to break the AI safety policy (self-approval, hallucinated accounts) to prove the controls actually hold.

## Phase 6 — Migration

See [migration-plan.md](./migration-plan.md) in full.

## Phase 7 — Pilot

**One entity, limited scope.** See [rollout-plan.md](./rollout-plan.md) for which entity and why.

## Phase 8 — Rollout

**Remaining entities, training, support.** See [rollout-plan.md](./rollout-plan.md) and [training-plan.md](./training-plan.md).

## Risks

See [risks.md](./risks.md) for the full register — carried across Phases 6-8 specifically, since that's where a real deployment's actual risk concentrates (this POC's Phases 0-5 risk was low: nothing here was live or irreversible).
