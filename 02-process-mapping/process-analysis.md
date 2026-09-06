# Process Analysis — Pain Points, Root Causes, and Fixes

Connects [current-state.md](./current-state.md) pain points to their root cause, the requirement that addresses them ([requirements.md](../01-discovery/requirements.md)), and the [future-state.md](./future-state.md) fix.

| Pain point | Root cause | Requirement(s) | Future-state fix |
|---|---|---|---|
| Close takes 12 days | Sequential manual handoffs between systems, each requiring re-validation | R01 | Automated close checklist; validation happens once, at ingestion, not repeatedly downstream |
| ~80% of reconciliations manual | No automated matching logic; matching is a spreadsheet exercise | R02 | Automated bank/AP/intercompany matching engine with exception queue |
| 100% manual billing → ERP entry | No integration between billing platform and ERP | R03 | API or file-based automated ingestion |
| ~35 intercompany exceptions/month | Reference/timing mismatches never validated at the point transactions are created | R04 | Automated intercompany matching on entity/reference/amount/currency/period |
| ~2 days to assemble reporting | Reports built by hand from multiple disconnected Excel exports | R05 | Reporting layer generated directly from the finance data model |
| Inconsistent approval evidence | No system of record for approvals — email/paper sign-off | R06, R12 | Enforced approval workflow with maker/checker separation and audit log |
| Inconsistent chart of accounts across entities | Each entity's ERP configured independently, never reconciled | R07 | Single entity-aware data model with one mapped CoA |
| Manual, inconsistent FX handling | No defined rate source or FX policy | R08 | Currency/FX model with a documented, auditable rate source |
| No single source of truth for master data | Informal, individually-maintained lookup spreadsheets | R09 | One authoritative master-data source per entity type |
| Duplicate invoices caught only at payment run | No validation at invoice entry | R10 | Automated duplicate detection during ingestion, before payment |
| No audit trail on posted-entry changes | Legacy ERP allows direct edits with no logging | R11 | Immutable audit log for all postings and edits |

## Why this ordering matters

Every pain point traces back to the same structural gap: **validation and matching logic exist only in people's heads and spreadsheets, applied downstream and inconsistently, rather than built into the data flow itself.** This is why PLAN.md's build order (§9) puts the data model, ingestion pipeline, and reconciliation engine before any AI — the deterministic fixes here solve most of the pain; AI is reserved for genuinely ambiguous classification, not for compensating for a missing data model.
