# Case Study — Northstar Finance OS

The PLAN.md §40 structure, in full. **A note on how to read "Results," specifically:** this is a fictional-client proof of concept, not a real deployment — so this document is careful throughout to separate what was *actually measured* in the POC itself (test results, real reconciliation match rates against real, if synthetic, data) from *business targets* that are assumptions about what a real deployment would achieve. The first is labelled **Achieved**. The second is labelled **Target**. Nothing here claims the second as the first.

## Problem

Northstar Health Group's close and reconciliation processes are manual and fragmented. Close takes ~12 business days. ~70% of journal entries are manual. Bank reconciliation is ~80% manual. Intercompany carries ~35 unresolved exceptions a month. Management reporting takes ~2 days to assemble by hand. There is no system-enforced approval workflow or audit trail. ([discovery-notes.md](../01-discovery/discovery-notes.md))

## Discovery

Three fictional stakeholder personas (CFO, Group Financial Controller, Shared Services Manager) were interviewed via a structured discovery script, producing a prioritised requirements table (R01–R12, each with a specific success metric) and a documented current-state process map. The consistent root cause across every pain point: validation and matching exist only in people's heads and spreadsheets, applied downstream and repeatedly, rather than once at the point data enters the system. ([01-discovery/](../01-discovery/), [process-analysis.md](../02-process-mapping/process-analysis.md))

## Current state

**[SHOW: current-state.md's ASCII flow]** — Billing → CSV/Manual Export → Excel → Legacy ERP → Finance Team → Manual Reconciliation → Manual Journals → Intercompany Matching → Reporting Workbook → PowerPoint → CFO. Every arrow in that chain is a manual, unvalidated handoff. ([current-state.md](../02-process-mapping/current-state.md))

## Solution

A target architecture with six layers — Sources, Integration, Core, AI, Controls, Outputs — built around one principle: validation happens once, at ingestion, not repeatedly downstream. Deterministic rules handle every accounting control; AI only assists with genuinely ambiguous classification, and never bypasses a control. ([system-architecture.md](../03-architecture/system-architecture.md), [future-state.md](../02-process-mapping/future-state.md))

## Build

- **SQL:** a 14-table PostgreSQL schema with debit=credit and maker≠checker enforced as real database constraints (a deferred trigger and a CHECK constraint), not just documented rules — proven by deliberately trying to break both. Six query sets covering AP, bank reconciliation, intercompany, close, reporting, and controls. ([05-sql/](../05-sql/))
- **Python:** an ingestion pipeline (schema validation → data-quality checks → duplicate detection → entity/account mapping → currency normalisation → DB load → reconciliation → exception report) plus a dedicated reconciliation engine with a four-tier matched/probable-match/unmatched output across bank, AP, and intercompany. ([06-python/](../06-python/))
- **API:** a FastAPI integration surface — customers, invoices, payments, journal entries, and four reporting endpoints — demonstrating request validation, idempotent invoice creation, a basic auth concept, and structured error handling. ([07-api/](../07-api/))
- **Accounting automation:** deterministic rules for vendor→account mapping, currency→FX requirement, duplicate/missing-field/intercompany-counterpart exceptions, and an approval-threshold-driven workflow — built and proven *before* any AI component, per the project's own critical design principle. ([08-accounting-automation/](../08-accounting-automation/))
- **AI:** a Claude-based accounting assistant (built and evaluated fully offline by deliberate choice — see [09-ai/README.md](../09-ai/README.md)) that calls directly into the deterministic rules above rather than a parallel copy of them, gated by a confidence threshold, a no-hallucinated-data check, and mandatory-reason overrides. ([09-ai/](../09-ai/))
- **Controls:** every phase has its own `controls.md` mapping each requirement to exactly where it's implemented and tested — not a single controls document written once and left to go stale.

## Results

### Achieved (measured in this POC)

- **128 automated tests, 128 passing**, spanning SQL constraints, Python pipeline logic, API behaviour, deterministic rules, AI safety policy, reconciliation logic, and dashboard metrics — run against real (if synthetic) data throughout, not mocked
- **Both hard accounting rules (debit=credit, maker≠checker) proven unbreakable** by deliberately trying to break them at the database level
- **Reconciliation engine matched 68/78 bank transactions and 36/48 intercompany transactions automatically** against realistically messy synthetic data, with every unmatched item carrying a specific reason ([06-python/reconciliation-engine-results.md](../06-python/reconciliation-engine-results.md))
- **The Phase 9 ingestion pipeline recovered 2 more invoices than a plain SQL load** via fuzzy vendor-name matching (88/92 vs. 86/92) — a real, measured improvement, not a claim
- **The AI evaluation found a genuine 9-10% inappropriate-automation rate** on its test set, disclosed and discussed rather than hidden, with two additional controls (amount-outlier detection, audit sampling) added in direct response ([09-ai/evaluation.md](../09-ai/evaluation.md))
- **Four real, unplanned bugs found and fixed** by actually running the code against real data rather than by code review alone — see Lessons, below
- **A genuine downstream finding, not a synthetic example:** the reconciliation engine independently surfaced that a duplicate-payment pair planted in Phase 7 was still causing real confusion in Phase 13's matching, three phases later ([06-python/README.md](../06-python/README.md))

### Target (business outcomes a real deployment would need to measure)

| Metric | Current state | Target | Status |
|---|---|---|---|
| Close duration | ~12 days | ≤7 days (R01) | **Target** — not measured; this POC has no real close cycle to time |
| Manual reconciliation | ~80% | ≤20% (R02) | **Target** |
| Intercompany exceptions | ~35/month | ≤10/month (R04) | **Target** |
| Reporting assembly | ~2 days | <4 hours (R05) | **Target** |
| Journal traceability | Inconsistent | 100%, system-enforced (R06) | **Target** — the *mechanism* (schema.sql's constraints) is built and proven; the *business outcome* requires a real deployment with real volume to confirm |

## Lessons

**Technical:** pandas silently turning blank values into `NaN` (which is truthy in Python) broke two separate blank-checks in the ingestion pipeline before being caught by actually running the code — see [06-python/README.md](../06-python/README.md). A SQL query missing three columns produced 264 false positives in the dashboard's data-quality check before being caught the same way. Both are now permanently regression-tested. The lesson generalises: review catches what you expect to look wrong; running the code against real data catches what you didn't think to check.

**Accounting:** the biggest structural fix wasn't a clever algorithm — it was moving validation to happen once, at the point data enters the system, instead of repeatedly downstream. Every current-state pain point traced back to the same root cause ([process-analysis.md](../02-process-mapping/process-analysis.md)), which meant the highest-leverage design decision was made in Phase 5, before a line of code existed.

**Implementation:** a rollout plan needs an explicit, stated assumption where real data doesn't exist yet (see [rollout-plan.md](../12-implementation/rollout-plan.md)'s pilot-entity selection) — pretending certainty you don't have is worse than flagging exactly what you assumed and why.

**AI-control:** the most valuable AI evaluation result wasn't the accuracy number — it was finding, and disclosing, a specific case that passed every documented control and was still wrong ([09-ai/evaluation.md](../09-ai/evaluation.md)). An AI safety policy that's never been shown to fail hasn't been tested hard enough yet.

## Next steps

What production would actually require, beyond this POC: real legacy data (this POC's messiness is deliberately planted, not extracted from a real system); a real API key and live-tested AI provider (this POC's `AnthropicLLMClient` is real, correct code, never exercised, by choice — see [09-ai/README.md](../09-ai/README.md)); the accounting-automation and AI rules wired into the live API rather than run as standalone scripts (a documented limitation in every relevant phase's `controls.md`); a confirmed (not assumed) approval threshold and audit-sample rate; and a real UAT cycle per [implementation-plan.md](../12-implementation/implementation-plan.md) Phase 5, specifically re-running this project's own deliberate control-break tests against production-like data and real users, not just synthetic data.

**[../KNOWN_ISSUES.md](../KNOWN_ISSUES.md)** consolidates every item above, plus every real bug found and fixed during development, into one page — the single place to see the full, honest state of what's built vs. what's assumed vs. what's genuinely unresolved.
