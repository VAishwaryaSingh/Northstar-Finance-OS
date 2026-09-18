# Bugs and detection — the short version

Everything is **synthetic** (a fictional healthcare group, fixed seed 42). Counts re-verified 2026-09-18 by re-running the
steps in [`2-process/run-logs/`](./2-process/run-logs/); committed result files came out byte-identical.

## 1. Bugs found and fixed: 4

All four were found by **running the code against data**, not by reading it.

| # | What went wrong | Where | Fix | Guard |
|---|---|---|---|---|
| 1 | Blank CSV cells did not reliably become `None` (`df.where(...)` left some as `NaN`) | [`06-python/validation.py`](../06-python/validation.py) | Clean each cell explicitly | Related test only: [`test_validation.py`](../06-python/tests/test_validation.py) — none specific to this pandas quirk |
| 2 | Blank-code checks silently passed: `NaN` is truthy in Python, so `if not value` and `is None` both missed it. Every blank check in ingestion was broken. | [`mappings.py`](../06-python/mappings.py), [`ingestion.py`](../06-python/ingestion.py) | `_blank()` helper; `pd.isna(...)` checks | Regression test `test_map_functions_treat_nan_as_blank_not_a_real_value` |
| 3 | Dashboard data-quality metric showed **281 findings; the real number was 17.** A query left out 3 of the 5 columns the rule checks, so all 88 invoices looked "missing" fields. 264 false positives. | [`10-dashboard/data.py`](../10-dashboard/data.py) | Added the missing columns | Regression test `test_data_quality_exceptions_has_no_false_missing_field_hits` |
| 4 | A deprecated Streamlit call (`use_container_width`) in the dashboard — minor | [`10-dashboard/`](../10-dashboard/) | Replaced | None dedicated |

[`KNOWN_ISSUES.md`](../KNOWN_ISSUES.md) lists bugs 1–3 with root causes. Bug 4 is recorded only in the commit message of the
dashboard commit ("feat: add Close Control Centre dashboard"), which is why the case study counts four and
`KNOWN_ISSUES.md` shows three.

## 2. What the system detects

| Layer | What it catches | Result on the seeded data |
|---|---|---|
| **Ingestion** ([`06-python/`](../06-python/)) | Missing entity codes · duplicate invoices · inconsistent vendor names | 92 invoices read, **88 loaded**, 36 exceptions in 5 categories |
| **Accounting rules** ([`08-accounting-automation/`](../08-accounting-automation/)) | Amount outliers · duplicate invoices · FX conversion needed · wrong account for vendor · intercompany with no counterpart | **47 findings**: 7 · 5 · 19 · 4 · 12 |
| **Reconciliation engine** ([`06-python/reconciliation_engine.py`](../06-python/reconciliation_engine.py)) | Bank, AP and intercompany items with no match | Bank 68 matched / 10 unmatched · AP 41 / 1 probable / 7 · Intercompany 36 / 12 |
| **Database constraints** ([`05-sql/schema.sql`](../05-sql/schema.sql)) | Unbalanced journals (debit ≠ credit) · self-approved journals (maker = checker) | Enforced in the database; tested by trying to break them |
| **AI safety policy** ([`09-ai/`](../09-ai/)) | Low confidence (< 0.95) · invented account/entity codes · failed rule check · amount ≥ 10,000 · vendor-history outlier · 5% random audit | 11 test cases, 8 sent to review; **1 wrongly auto-approved (9%)** |

### Planted issues vs. caught

Every problem deliberately injected into the data is logged in [`04-data/data-quality-log.md`](../04-data/data-quality-log.md).
Detail: [seeded-issues-vs-detected.md](./1-data/seeded-issues-vs-detected.md).

| Planted issue | Planted | Caught |
|---|---|---|
| Missing entity code | 7 | **7** |
| Inconsistent vendor name | 2 | **2** |
| Unmatched bank transaction | 22 | **22** accounted for (10 unmatched by design, 10 re-matched, 2 excluded at load) |
| Unmatched intercompany | 12 | **12** (two independent detectors agree) |
| Duplicate invoice | 6 | **5** — the 6th pair is masked by a blank entity code |
| Incorrect account mapping | 5 | **4** — the 5th is masked by a blank entity code |
| Duplicate payment | 4 | **0** |
| Late-posted journal | 2 | **0** |
| Unapplied cash (payment with no invoice) | 5 | **0** |

## 3. What it does not detect

- **Duplicate payments, late-posted journals, unapplied cash: no dedicated detector exists.** They are planted and they
  load. Duplicate payments show up only indirectly, through one odd AP reconciliation match. These are not yet listed in
  `KNOWN_ISSUES.md`.
- **The two "masked" misses** (6th duplicate invoice, 5th mis-mapping): both records also have a blank entity code, so they
  are excluded at load before those rules run. Documented and explainable, but still not caught.
- **The AI assistant has a known failure.** Case `EVAL-010` passed every documented control and was still wrong.
  Disclosed, not tuned away. The real-model integration was never run live; results come from a mock model.
- **The amount-outlier rule is probably too sensitive.** It flagged 7 of 49 AP invoices (~14%).
- "Caught" means caught against a **planted** answer key. It says nothing about real, unplanned errors.
