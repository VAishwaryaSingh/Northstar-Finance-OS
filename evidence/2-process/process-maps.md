# Process: from discovery to a working pipeline

How the work moved from "what is broken" to "what was built and run". Excerpts below are copied from the source files;
follow the links for the full documents. The client and the discovery interviews are **fictional** (a simulated script,
not a real engagement — see the [README](../../README.md#whats-fictional-vs-actually-implemented)).

## 1. Current state — where the problem sits

From [`02-process-mapping/current-state.md`](../../02-process-mapping/current-state.md), based on
[`discovery-notes.md`](../../01-discovery/discovery-notes.md):

```text
Billing System → CSV / Manual Export → Excel → Legacy ERP → Finance Team → Manual Reconciliation
→ Manual Journals → Intercompany Matching → Reporting Workbook → PowerPoint → CFO
```

Every arrow is a manual handoff. Baseline figures from discovery (fictional client): close ≈ 12 business days,
≈ 70% of journals manual, ≈ 80% of reconciliation manual, ≈ 35 unresolved intercompany exceptions a month,
≈ 2 days to assemble management reporting.

## 2. Root cause

From [`process-analysis.md`](../../02-process-mapping/process-analysis.md):

> Every pain point traces back to the same structural gap: **validation and matching logic exist only in people's heads
> and spreadsheets, applied downstream and inconsistently, rather than built into the data flow itself.**

Each pain point is mapped to a root cause, a requirement (R01–R12 in
[`requirements.md`](../../01-discovery/requirements.md)), and a future-state fix. For example:

| Pain point | Requirement | Future-state fix |
|---|---|---|
| ~80% of reconciliations manual | R02 | Automated bank/AP/intercompany matching engine with an exception queue |
| Duplicate invoices caught only at payment run | R10 | Automated duplicate detection during ingestion, before payment |
| ~35 intercompany exceptions/month | R04 | Matching on entity / reference / amount / currency / period |

## 3. Future state — the design

From [`02-process-mapping/future-state.md`](../../02-process-mapping/future-state.md):

```text
Source Systems (Billing, Banking, AP, Existing ERP) → Integration / Ingestion → Validation + Normalisation
→ Finance Data Model → Accounting Rules / AI Assistance → Human Approval → Journal / Subledger Posting
→ Automated Reconciliation → Close Control Centre → CFO Reporting
```

Architecture detail: [`03-architecture/system-architecture.md`](../../03-architecture/system-architecture.md), with the
key decisions in [`ADRs/`](../../ADRs/).

## 4. Design → deliverable → proof

Each design element became a working, tested piece of the repo. The proof column points at something that was run, not
just written:

| Design element | Built in | Proof it ran |
|---|---|---|
| Finance data model with DB-enforced controls | [`05-sql/`](../../05-sql/) | Constraint tests (debit = credit; maker ≠ checker) — see [`pytest-summary.txt`](./run-logs/pytest-summary.txt) |
| Validate once, at ingestion | [`06-python/`](../../06-python/) | [`exception-report.md`](../../06-python/exception-report.md): 92 invoices read, 88 loaded, 36 exceptions in 5 categories |
| Automated reconciliation | [`06-python/reconciliation_engine.py`](../../06-python/reconciliation_engine.py) | [`reconciliation-run.txt`](./run-logs/reconciliation-run.txt) |
| Accounting rules before AI | [`08-accounting-automation/`](../../08-accounting-automation/) | [`rules-run.txt`](./run-logs/rules-run.txt) — 47 findings, 5 rules |
| AI assistant with a safety policy | [`09-ai/`](../../09-ai/) | [`evaluation-results.md`](../../09-ai/evaluation-results.md) — 11 cases, incl. a disclosed failure |
| Close Control Centre | [`10-dashboard/`](../../10-dashboard/) | [Live dashboard](https://northstar-finance-os-bndfmftzjicmew2hvehcdx.streamlit.app/) |

## 5. Bugs the process itself exposed

Four real, unplanned bugs were found by running code against data rather than by reviewing it — full list with fixes in
[bugs-and-detection.md](../bugs-and-detection.md). Two examples: blank CSV cells silently becoming `NaN` instead of `None`
(and `NaN` is truthy in Python, so "is this blank?" checks let it through), and a dashboard metric that reported 281 findings
when the real number was 17 because a query was missing columns the rule checks.
