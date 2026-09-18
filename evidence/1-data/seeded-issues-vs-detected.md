# Seeded issues vs. what the system actually caught

The synthetic dataset is **deliberately messy**. Every problem injected into it is logged at generation time to
[`04-data/data-quality-log.md`](../../04-data/data-quality-log.md) — that file is the ground truth. This page checks each
planted category against what the pipeline, rules and reconciliation engine actually found when run against the real
database, so the claim "the system catches these" is testable rather than asserted.

All data is synthetic (fixed seed 42). The counts below were re-verified on 2026-09-18 by re-running the pipeline steps
in [`../2-process/run-logs/`](../2-process/run-logs/) — the committed result files came out byte-identical.

## Scorecard

| Planted issue | Planted | Caught | Where it is caught | Note |
|---|---|---|---|---|
| Missing entity code | 7 | **7 / 7** | Ingestion → [`exception-report.md`](../../06-python/exception-report.md) | 4 invoices excluded from load, 3 bank lines |
| Inconsistent vendor name | 2 | **2 / 2** | Ingestion fuzzy match (`Med Supplies Ltd`, `Medical Supplies Limited` → `Medical Supplies Ltd`) | Invoices loaded: 88 / 92 vs. 86 / 92 with a plain SQL load |
| Unmatched bank transaction | 22 | **22 / 22 accounted for** | Reconciliation engine → [`reconciliation-engine-results.md`](../../06-python/reconciliation-engine-results.md) | See breakdown below |
| Unmatched intercompany | 12 | **12 / 12** | Reconciliation engine (12 unmatched) **and** rule `intercompany_no_counterpart` (12) | Two independent detectors agree |
| Duplicate invoice | 6 | **5 / 6** | Ingestion, rule `duplicate_invoice`, and SQL `ap.sql` — all find the same 5 | 6th pair explained below |
| Incorrect account mapping | 5 | **4 / 5** | Rule `incorrect_account_mapping` → [`rule-findings.md`](../../08-accounting-automation/rule-findings.md) | 5th explained below |
| Duplicate payment | 4 | **No dedicated detector** | — | See "Gaps" |
| Late transaction (journal) | 2 | **No dedicated detector** | — | See "Gaps" |
| Missing invoice reference (unapplied cash) | 5 | **No dedicated detector** | — | See "Gaps" |

**In short:** 4 categories fully caught, 2 caught with a documented and explainable shortfall, 3 with no automated
detector. The third group is stated here rather than left for a reviewer to discover.

## The two "almost" cases

Both shortfalls have the same cause — two *independent* planted issues landed on the same record:

- **Duplicate invoice, 5 of 6.** The 6th pair is `INV-0004` / `INV-0091`. `INV-0004` is also one of the rows with a blank
  `entity_code`, so it is excluded at load *before* duplicate detection runs, leaving `INV-0091` looking like an ordinary
  invoice. Documented in [`KNOWN_ISSUES.md` §2](../../KNOWN_ISSUES.md) and [`06-python/README.md`](../../06-python/README.md).
- **Incorrect account mapping, 4 of 5.** The four caught are `INV-0046`, `INV-0051`, `INV-0055`, `INV-0085`. The fifth,
  `INV-0029`, is also a blank-`entity_code` row (see the missing-entity list in the data-quality log), so it never reaches
  the rule — the rule ran over the 88 loaded invoices.

## Unmatched bank transactions: 22 planted → what happened to each

| Outcome | Count | Rows | Why |
|---|---|---|---|
| Left **unmatched** by the engine | 10 | `BANK-0072` … `BANK-0081` | Bank charges with no payment record. Unmatched is the *correct* answer — they need a manual journal |
| **Recovered** as matched | 10 | `BANK-0007, 0008, 0015, 0022, 0024, 0031, 0047, 0048, 0061, 0071` | Amount/timing mismatches against a payment; the engine's tolerance windows re-match them |
| **Excluded at load** | 2 | `BANK-0060`, `BANK-0070` | Also blank-`entity_code` rows |

Engine total for bank: 68 matched, 0 probable, 10 unmatched (78 lines — the 81 source lines minus 3 excluded).

## Gaps: seeded, but no dedicated detector

Based on searching this repo's SQL, Python, API, dashboard and docs, nothing detects the following as a category. These
records are planted and load into the database, but no check or exception report is aimed at them:

- **Duplicate payments (4 pairs).** The only visible trace is indirect: the AP reconciliation engine's one
  `probable_match` (`INV-0059` ↔ `PAY-0071`) is a side-effect of the `PAY-0062` / `PAY-0071` duplicate pair for `INV-0086`
  — see [`06-python/README.md`](../../06-python/README.md) ("Phase 13"). Evidence of that indirect symptom exists for one of
  the four pairs only.
- **Late-posted journals (`JE-0031`, `JE-0036`).** Entry date falls in an earlier month than the tagged close period.
  No period-cut-off check exists.
- **Unapplied cash receipts (`PAY-0072` … `PAY-0076`).** Payments with no `invoice_id`. The API deliberately allows this
  (`invoice_id` is optional); there is no exception category or ageing check for it.

These are natural next controls (a payment-duplicate rule, a period cut-off rule, an unapplied-cash report) rather than
hidden defects — but they are not built, and they are not currently listed in
[`KNOWN_ISSUES.md`](../../KNOWN_ISSUES.md).

## Reproduce

```bash
python 04-data/generate_data.py                   # regenerates the CSVs and data-quality-log.md (deterministic)
.venv/bin/python 06-python/ingestion.py           # rewrites exception-report.md (reloads the database)
.venv/bin/python 06-python/run_reconciliation.py  # rewrites reconciliation-engine-results.md
.venv/bin/python 08-accounting-automation/run_rules.py   # rewrites rule-findings.md
```
