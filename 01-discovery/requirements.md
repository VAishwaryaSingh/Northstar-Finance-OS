# Requirements — Northstar Health Group

Derived from the prioritised problem statement in [discovery-script.md](./discovery-script.md) and the detail in [discovery-notes.md](./discovery-notes.md). Priority: **P0** = blocking the core close/reconciliation problem, **P1** = important but not blocking.

| ID | Problem | Requirement | Priority | Success Metric |
|---|---|---|---|---|
| R01 | Slow close (12 days) | Automate close workflow with a tracked checklist and parallel-capable tasks | P0 | ≤7 days |
| R02 | Manual reconciliations (~80%) | Automated bank/AP/intercompany reconciliation with exception queue | P0 | ≤20% manual |
| R03 | Manual billing → ERP re-keying (100%) | API or automated file-based ingestion from billing platform | P0 | 0% manual |
| R04 | Intercompany mismatches (~35/month) | Automated intercompany matching by reference/amount/entity/currency/period | P0 | ≤10 exceptions/month |
| R05 | Manual reporting (~2 days) | Automated reporting layer sourced from the finance data model | P1 | <4 hours |
| R06 | Inconsistent journal approval evidence | Enforced approval workflow with full audit trail | P0 | 100% journal traceability |
| R07 | Inconsistent chart of accounts / entity setup across entities | Entity-aware accounting model with a single mapped chart of accounts | P0 | All entities supported on one model |
| R08 | Manual, inconsistent FX handling | Currency + FX model with a defined, auditable rate source | P1 | GBP/USD supported with documented FX policy |
| R09 | No single source of truth for customers/vendors/CoA | Master-data model with one authoritative source per entity type | P1 | Zero informally-maintained lookup spreadsheets |
| R10 | Duplicate invoices caught late (only at payment run) | Automated duplicate-invoice detection at ingestion | P0 | Duplicates flagged before payment, not after |
| R11 | No system-enforced audit trail on posted-entry changes | Immutable audit log for all postings and edits | P0 | 100% of changes attributable to a user and timestamp |
| R12 | No maker/checker enforcement on journal creation | Role-based access with segregation of duties (creator ≠ approver) | P1 | No self-approved journals above threshold |

This table should be revisited whenever a new phase (architecture, data model, AI workflow) surfaces a requirement not captured here.
