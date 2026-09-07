# Executive Summary — Northstar Finance OS

Written to the PLAN.md §41 two-page structure — designed to be exported to a two-page PDF (any markdown-to-PDF tool, e.g. Pandoc) rather than checked into this repository as a binary file, consistent with the project's preference for reviewable, diffable source over generated output. This markdown file is that source.

---

## Page 1

### Project

**Northstar Finance OS** — an end-to-end finance transformation and AI-native ERP proof of concept.

### Fictional client

**Northstar Health Group** — a fictional UK/US multi-entity healthcare group (Northstar Health Holdings Ltd (UK), Northstar Health Services Inc (US), Northstar Shared Services Ltd (UK)), GBP/USD, ~5,000 transactions/month. Entirely fictional — see [AGENTS.md](../AGENTS.md).

### Problem

Close takes ~12 business days. ~70% of journals are manual. Bank reconciliation is ~80% manual. Intercompany carries ~35 unresolved exceptions/month. Management reporting takes ~2 days to assemble by hand. No system-enforced approval workflow or audit trail exists.

### Current state

Billing → CSV/manual export → Excel → legacy ERP → manual reconciliation → manual journals → intercompany matching → reporting workbook → PowerPoint → CFO. Every handoff is manual and unvalidated; problems surface downstream, during reconciliation, rather than at the point of entry.

### Target state

One integration layer (API where a source supports it, file ingestion elsewhere) feeding one finance data model with a single shared chart of accounts, deterministic accounting rules, AI assistance only for genuinely ambiguous cases (never bypassing a control), full audit logging, and a live Close Control Centre dashboard.

### Architecture

```text
Sources → Integration → Core → AI → Controls → Outputs
(Billing,  (API/CSV,     (Data   (Suggests,  (Approvals,  (Trial balance,
 Banking,   validation)   model,  never       audit log,   dashboard,
 AP, ERP)                 rules)  decides)    thresholds)  reporting)
```

Full diagram: [system-architecture.md](../03-architecture/system-architecture.md).

### Key metrics (this POC, actually measured)

128/128 automated tests passing · both hard accounting rules (debit=credit, maker≠checker) proven unbreakable at the database level · 68/78 bank transactions and 36/48 intercompany transactions matched automatically against realistically messy data · 4 real bugs found and fixed by running the code, not just reviewing it.

---

## Page 2

### Solution

A six-layer target architecture built around one principle: validate once, at ingestion, not repeatedly downstream. Deterministic rules run first and handle every accounting control; AI assists only where rules can't resolve ambiguity, and is checked by the same rules a human-entered transaction would be checked by — not a separate, potentially-drifting opinion.

### Technical build

PostgreSQL (14-table schema, constraints enforced by the database itself) · Python (ingestion pipeline, reconciliation engine) · FastAPI (REST integration layer, idempotent posting) · deterministic accounting-automation rules · a Claude-based AI assistant with a documented, tested safety policy · a live Streamlit dashboard drawing on all of the above.

### Controls

Debit=credit and maker≠checker enforced as real database constraints, not documentation. Every AI recommendation passes a confidence threshold, a no-hallucinated-data check, and the exact same deterministic rule a human transaction would face, before it can avoid human review. Every override requires a non-blank reason. A random-sampling control covers the residual risk category no single rule can close — disclosed honestly in [09-ai/evaluation.md](../09-ai/evaluation.md), including the one evaluation case that still wasn't caught.

### Implementation plan

A 9-phase methodology (Discovery through Rollout, ~19-32 weeks for a real deployment at this client's scale), a migration plan with an explicitly-stated pilot-entity assumption, a 10-item risk register, and a staged rollout (pilot on one GBP-only entity, the US entity last, specifically to de-risk FX logic). Full detail: [12-implementation/](../12-implementation/).

### Lessons

The highest-leverage decision was architectural (validate once, at ingestion), made before any code existed. Two real bugs were found only by running code against real data, not by review. The most valuable AI-evaluation result was a disclosed failure, not a clean pass rate. Full discussion: [case-study.md](./case-study.md)'s Lessons section.

### Portfolio / GitHub

Full repository, including every phase's own README/`controls.md`, the complete test suite, and this document's source: *(link added once the repository is public — see the project's own README for current status)*.
