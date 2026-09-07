# Discovery-to-Demo Story

PLAN.md §35 is explicit about what this demo must not be:

> "Here are some cool features I built."

And what it must be instead:

> "You told me X. We found Y. Therefore we designed Z. Here's how it solves the problem. Here's the control model. Here's how we'd implement it."

This document is that chain, made explicit for each of the five pain points [demo-script.md](./demo-script.md)'s discovery recap names — so nothing in the demo is a feature shown because it exists, only because a specific thing the customer said led to it.

## 1. Close takes 12 days

- **You told me:** close takes ~12 business days; the first week is data collection and reconciliation, the second is journal review, intercompany resolution, and reporting ([discovery-notes.md](../01-discovery/discovery-notes.md))
- **We found:** every handoff between systems is manual and unvalidated at the point of transfer — problems are discovered downstream during reconciliation, not caught at entry ([current-state.md](../02-process-mapping/current-state.md)'s root pattern)
- **Therefore we designed:** validation once, at ingestion, not repeatedly downstream ([future-state.md](../02-process-mapping/future-state.md))
- **Here's how it solves it:** [06-python/ingestion.py](../06-python/ingestion.py)'s pipeline — schema validation, data-quality checks, and mapping all happen the moment data arrives, not when someone notices a problem three steps later
- **Here's the control model:** every exception is logged with a reason ([06-python/exception-report.md](../06-python/exception-report.md)), not silently dropped or silently fixed
- **Here's how we'd implement it:** [12-implementation/implementation-plan.md](../12-implementation/implementation-plan.md) Phase 3 (Integration) — pilot on one entity first, per [rollout-plan.md](../12-implementation/rollout-plan.md)

## 2. Reconciliations are ~80% manual

- **You told me:** bank reconciliation is done monthly in Excel against bank CSV exports, ~80% of reconciling items resolved by hand ([discovery-notes.md](../01-discovery/discovery-notes.md))
- **We found:** no automated matching logic exists — matching is a spreadsheet exercise, redone every month from scratch ([process-analysis.md](../02-process-mapping/process-analysis.md))
- **Therefore we designed:** a dedicated reconciliation engine with a real matched/probable-match/unmatched output, not a binary yes/no
- **Here's how it solves it:** [06-python/reconciliation_engine.py](../06-python/reconciliation_engine.py) — proven against real data at [06-python/reconciliation-engine-results.md](../06-python/reconciliation-engine-results.md): 68 of 78 bank transactions matched automatically, with the 10 unmatched ones flagged with a specific reason, not just left unexplained
- **Here's the control model:** matches are computed independently from amount/date/counterparty — never just trusting a label the source data happened to carry (see that file's own header comment on why)
- **Here's how we'd implement it:** [migration-plan.md](../12-implementation/migration-plan.md)'s Validation section — reconciliation results are one of the five things checked before any entity's legacy system is retired

## 3. ~35 intercompany exceptions a month

- **You told me:** intercompany balances are tracked in a shared spreadsheet, matched manually between entity controllers, ~35 exceptions carried forward every month ([discovery-notes.md](../01-discovery/discovery-notes.md))
- **We found:** reference and timing mismatches are never validated at the point transactions are created — only discovered when someone tries to reconcile them ([process-analysis.md](../02-process-mapping/process-analysis.md))
- **Therefore we designed:** automated matching on entity pair, reference, amount, currency, *and* period — not just reference and amount
- **Here's how it solves it:** [06-python/reconciliation_engine.py](../06-python/reconciliation_engine.py)'s `reconcile_intercompany` — proven against real data: 12 of 48 transactions genuinely unmatched, each with a specific reason (no counterpart at all, vs. a counterpart that exists but disagrees on period or amount)
- **Here's the control model:** [08-accounting-automation/exception_rules.py](../08-accounting-automation/exception_rules.py)'s `check_intercompany_counterpart` runs the same check as a standing policy rule, live, on the dashboard — not just a month-end report
- **Here's how we'd implement it:** intercompany balances get a live reconciliation exercise *before* cutover, not a straight data copy ([migration-plan.md](../12-implementation/migration-plan.md)'s Data Inventory section)

## 4. Reporting takes ~2 days to assemble

- **You told me:** management reporting takes ~2 days to assemble by hand from multiple Excel exports ([discovery-notes.md](../01-discovery/discovery-notes.md))
- **We found:** reports are built by hand from disconnected exports because there's no single place the data already lives in reportable form ([process-analysis.md](../02-process-mapping/process-analysis.md))
- **Therefore we designed:** a reporting layer generated directly from the finance data model, not assembled from exports of it
- **Here's how it solves it:** [07-api](../07-api/)'s `GET /trial-balance` and related endpoints, and the [Close Control Centre dashboard](../10-dashboard/) — the same close-progress and financial data the CFO wants is one page load, not a two-day exercise
- **Here's the control model:** every number on the dashboard is a live query against the actual database ([10-dashboard/dashboard-spec.md](../10-dashboard/dashboard-spec.md)) — not a cached snapshot someone has to remember to refresh
- **Here's how we'd implement it:** UAT in [implementation-plan.md](../12-implementation/implementation-plan.md) Phase 5 specifically has the CFO/Controller personas use the dashboard against a parallel-run period before go-live, not just the finance team

## 5. No system of record for controls

- **You told me:** any Shared Services team member with ERP access can create a journal entry, with no enforced maker/checker distinction; changes to posted entries are possible with no audit trail ([discovery-notes.md](../01-discovery/discovery-notes.md))
- **We found:** approval is a manual sign-off convention (email, paper), inconsistently evidenced — not a system-enforced rule ([current-state.md](../02-process-mapping/current-state.md))
- **Therefore we designed:** maker≠checker and debit=credit as database-level constraints, not application-level suggestions
- **Here's how it solves it:** [05-sql/schema.sql](../05-sql/schema.sql)'s deferred trigger and CHECK constraint — and this was actually tested by deliberately trying to break both rules (see that file's own tests), not just documented as a policy
- **Here's the control model:** every one of Phase 12's AI safety requirements — confidence threshold, human review, no-hallucinated-data check, mandatory override reason — is enforced the same way: as code that runs, not a policy that's written down ([09-ai/controls.md](../09-ai/controls.md))
- **Here's how we'd implement it:** [12-implementation/risks.md](../12-implementation/risks.md) R4 specifically calls out re-testing these exact deliberate-break scenarios against production-like data in UAT, before any entity goes live — not assuming what worked on synthetic data generalises

## Why this document exists separately from the script itself

[demo-script.md](./demo-script.md) is what gets *said*, timed to 10 minutes. This document is the underlying justification for every section of it — useful for answering "why did you build it that way" follow-up questions that go past what the timed script covers, and for adapting the demo to a customer who wants to spend all 10 minutes on one of these five threads instead of moving through all five.
