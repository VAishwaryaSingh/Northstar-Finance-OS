# Evidence

A guided path through the proof behind Northstar Finance OS: **the data it works on, the process that produced the
system, and the outcome it reached** — with links straight to the working files instead of a tour of thirteen folders.

> **Everything here is synthetic.** The client (Northstar Health Group), its entities, customers, vendors and every
> transaction are fictional, generated deterministically (seed 42). Business outcomes that a real deployment would need to
> measure are labelled **Target**, not achieved. Counts on these pages were re-verified on 2026-09-18.

## 1. Underlying data — what the system was given

| | |
|---|---|
| [Sample extracts](./1-data/sample-extracts.md) | The first rows of the four raw source files (invoices, payments, bank, intercompany), blanks and all |
| [Seeded issues vs. detected](./1-data/seeded-issues-vs-detected.md) | Every problem deliberately planted in the data, checked against what the system caught — including 3 categories with no detector |
| Full dataset | [`04-data/`](../04-data/) — 11 CSVs (509 rows), the generator, and the [ground-truth log](../04-data/data-quality-log.md) |

## 2. Our process — how it was built and run

| | |
|---|---|
| [Discovery to deliverable](./2-process/process-maps.md) | Current-state problem → root cause → future-state design → what was built and how it was proven |
| [Run logs](./2-process/run-logs/) | Captured output: [128 tests passing](./2-process/run-logs/pytest-summary.txt), [reconciliation engine](./2-process/run-logs/reconciliation-run.txt), [accounting rules](./2-process/run-logs/rules-run.txt) |
| Source documents | [Discovery](../01-discovery/) · [process maps](../02-process-mapping/) · [architecture](../03-architecture/) · [ADRs](../ADRs/) |

## 3. Outcome — what it produced

| | |
|---|---|
| [Results summary](./3-outcome/results-summary.md) | Measured results, the AI evaluation (including its disclosed failure), and the Target-not-measured table |
| [Live dashboard](https://northstar-finance-os-bndfmftzjicmew2hvehcdx.streamlit.app/) | The Close Control Centre, running on the same synthetic data — no login |
| Detailed outputs | [Reconciliation results](../06-python/reconciliation-engine-results.md) · [exception report](../06-python/exception-report.md) · [rule findings](../08-accounting-automation/rule-findings.md) · [AI evaluation](../09-ai/evaluation-results.md) |

## Reproduce it

```bash
sudo service postgresql start
.venv/bin/pytest                                          # 128 tests, against the real database
.venv/bin/python 06-python/run_reconciliation.py          # rewrites the reconciliation results
.venv/bin/python 08-accounting-automation/run_rules.py    # rewrites the rule findings
```

Full setup is in the [main README](../README.md#how-do-i-run-it). Known bugs, assumptions and scope limits:
[`KNOWN_ISSUES.md`](../KNOWN_ISSUES.md).
