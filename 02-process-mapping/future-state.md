# Future-State Process — Northstar Health Group

Target design addressing the root pattern identified in [current-state.md](./current-state.md): manual, unvalidated handoffs between systems. See [process-analysis.md](./process-analysis.md) for the mapping from each current-state pain point to its future-state fix, and [requirements.md](../01-discovery/requirements.md) for the requirements this satisfies.

```text
Source Systems
 ├── Billing
 ├── Banking
 ├── AP
 └── Existing ERP
        ↓
Integration / Ingestion Layer
        ↓
Validation + Normalisation
        ↓
Finance Data Model
        ↓
Accounting Rules / AI Assistance
        ↓
Human Approval
        ↓
Journal / Subledger Posting
        ↓
Automated Reconciliation
        ↓
Close Control Centre
        ↓
CFO Reporting
```

## What changes at each stage

| Stage | Current state | Future state |
|---|---|---|
| Source → ingestion | Manual export, manual re-keying | Automated ingestion (API where available, structured file import otherwise) — see [system-architecture.md](../03-architecture/system-architecture.md) |
| Validation | None at point of entry — errors found during reconciliation | Schema validation, duplicate detection, and mapping checks run immediately on ingestion |
| Data model | Fragmented per-entity spreadsheets and inconsistent CoA | Single entity-aware finance data model (see PLAN.md §18) — one CoA, mapped consistently across entities |
| Classification | Manual judgement, undocumented | Deterministic rules first (vendor→account, entity→ledger, currency→FX); AI assists only on ambiguous/exception cases, always with a confidence score and evidence |
| Approval | Email/paper sign-off, inconsistently evidenced | Enforced approval workflow with maker/checker separation and full audit log |
| Posting | Manual entry, editable with no trail | System-enforced posting; balanced (debit=credit) by construction; audit-logged |
| Reconciliation | Manual, ~80% by hand | Automated bank/AP/intercompany matching with an exception queue for what doesn't auto-match |
| Reporting | Manual assembly, ~2 days | Reporting layer generated directly from the finance data model |

## Critical design principle

**AI should assist accounting decisions but must not bypass accounting controls.** Deterministic validation and approval thresholds are enforced regardless of AI confidence; AI recommendations that fail a check, or fall below the confidence threshold, are routed to human review rather than auto-posted (see PLAN.md §25 for the exact policy once implemented in Phase 12).
