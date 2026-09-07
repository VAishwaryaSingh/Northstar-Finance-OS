# Target System Architecture — Northstar Finance OS

Turns the future-state flow in [future-state.md](../02-process-mapping/future-state.md) into a concrete set of system components, organised into the six layers from PLAN.md §17. Each component is traced to the requirement(s) it exists to satisfy — see [requirements.md](../01-discovery/requirements.md) for R01–R12.

See also: [integration-map.md](./integration-map.md) for how each source actually connects in, and [security-model.md](./security-model.md) for auth/roles/audit.

```text
 SOURCES                INTEGRATION                  CORE                    AI                    CONTROLS                 OUTPUTS
┌──────────┐        ┌──────────────────┐      ┌──────────────────┐    ┌──────────────────┐   ┌──────────────────┐    ┌──────────────────┐
│ Billing  │──┐     │                  │      │ Finance Data      │    │ Classification    │   │ Approvals         │    │ Trial Balance     │
├──────────┤  │     │ API ingestion    │      │ Model             │    │ (vendor/account/   │   │ (maker/checker)   │    ├──────────────────┤
│ Banking  │──┼────▶│ CSV ingestion    │─────▶│ Journal Engine    │◀──▶│  entity, ambiguous │──▶│ Role Permissions  │───▶│ Reconciliations   │
├──────────┤  │     │ Validation       │      │ Reconciliation    │    │  cases only)       │   │ Audit Logs        │    ├──────────────────┤
│ AP       │──┤     │ Transformation   │      │ Engine            │    │ Exception          │   │ Confidence        │    │ Close Dashboard   │
├──────────┤  │     │                  │      │ Intercompany      │    │ Explanation        │   │  Thresholds       │    ├──────────────────┤
│ Legacy   │──┘     │                  │      │ Engine            │    │ Suggested          │   │ Exception Queues  │    │ Management        │
│ ERP      │        │                  │      │ Workflow Engine   │    │  Treatment         │   │                   │    │  Reporting        │
└──────────┘        └──────────────────┘      └──────────────────┘    │ Anomaly Detection   │   └──────────────────┘    └──────────────────┘
                                                                        └──────────────────┘
                     failed validation ──▶ exception queue (Controls), never silently dropped
                     AI output below confidence threshold, or failing a control check ──▶ human approval (Controls), never auto-posted
```

## Sources

| Component | Description | Requirement(s) |
|---|---|---|
| Billing | External billing platform — source of customer invoices | R03 |
| Banking | Bank statement feeds per entity/currency | R02, R08 |
| AP | Accounts payable / vendor invoice source | R02, R10 |
| Legacy ERP | Existing per-entity ERP, retained as a read source during transition (see [ADR-0004](../ADRs/0004-retain-legacy-erp-initially.md)) | R07, R09 |

## Integration

| Component | Description | Requirement(s) |
|---|---|---|
| API ingestion | Structured API pull/push where the source supports it (billing platform) | R03 |
| CSV ingestion | Structured file import for sources without an API (banking, AP, legacy ERP exports) | R02, R03 |
| Validation | Schema validation, duplicate detection, mapping checks run at the point of ingestion, not downstream | R10, R11 |
| Transformation | Currency normalisation, entity/account mapping into the single chart of accounts | R07, R08, R09 |

Why both API and CSV ingestion rather than standardising on one: [ADR-0002](../ADRs/0002-api-and-csv-ingestion.md).

## Core

| Component | Description | Requirement(s) |
|---|---|---|
| Finance Data Model | Single entity-aware relational model — one chart of accounts, mapped consistently across entities (built in Phase 6, PLAN.md §18) | R07, R09 |
| Journal Engine | Enforces balanced (debit = credit) postings by construction; every posting is audit-logged | R06, R11 |
| Reconciliation Engine | Automated bank/AP matching with an exception queue for what doesn't auto-match | R02 |
| Intercompany Engine | Automated matching by entity/reference/amount/currency/period | R04 |
| Workflow Engine | Tracks the close checklist and routes tasks/approvals | R01, R06 |

## AI

Deterministic rules run first; AI is reserved for genuinely ambiguous classification and never bypasses a control — this is a first-class design principle, not an implementation detail. See [ADR-0003](../ADRs/0003-deterministic-rules-before-ai.md) and the future-state critical design principle it formalises.

| Component | Description | Requirement(s) |
|---|---|---|
| Classification | Suggests vendor→account, entity→ledger, currency→FX mapping only when deterministic rules don't already resolve it | R07, R08 |
| Exception Explanation | Plain-language explanation of why a transaction landed in an exception queue | R02, R04 |
| Suggested Accounting Treatment | Proposes journal treatment for ambiguous transactions, always with a confidence score and supporting evidence | — (supports R01 close speed indirectly) |
| Anomaly Detection | Flags transactions that look unusual against historical pattern (e.g. duplicate-invoice candidates) | R10 |

Every AI output that fails a control check or falls below the confidence threshold is routed to human review, never auto-posted (PLAN.md §25, implemented in Phase 12).

## Controls

| Component | Description | Requirement(s) |
|---|---|---|
| Approvals | Maker/checker workflow — the creator of a journal cannot also approve it | R06, R12 |
| Role Permissions | Role-based access enforcing segregation of duties | R12 |
| Audit Logs | Immutable log of all postings and edits, attributable to a user and timestamp | R11 |
| Confidence Thresholds | Minimum AI confidence required before a suggestion can even reach a human approver as "ready to post" | supports AI safety policy, PLAN.md §25 |
| Exception Queues | Holding area for anything that fails validation, fails matching, or falls below AI confidence — nothing is silently dropped | R02, R04, R10 |

Full role/permission detail: [security-model.md](./security-model.md).

## Outputs

| Component | Description | Requirement(s) |
|---|---|---|
| Trial Balance | Generated directly from the finance data model | R05 |
| Reconciliations | Bank/AP/intercompany reconciliation status and exception detail | R02, R04 |
| Close Dashboard | Close progress, unreconciled items, unapproved journals, AI recommendations pending review (built in Phase 14) | R01 |
| Management Reporting | Revenue/expense by entity, monthly movement, currency exposure | R05 |

## Requirement coverage check

Every requirement R01–R12 is addressed by at least one component above. R01 (close speed) and R05 (reporting speed) are satisfied by the architecture collectively (Workflow Engine + Outputs) rather than a single component, since they are outcomes of removing manual handoffs, not a single system to build.
