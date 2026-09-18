# Outcome: what was measured, and what was not

This page separates **what this proof of concept actually measured** from **business outcomes a real deployment would need
to measure**. The client and all data are fictional and synthetic, so there is no real close cycle to time. Wording follows
[`13-case-study/case-study.md`](../../13-case-study/case-study.md), which draws the same line.

Counts were re-verified on 2026-09-18 — see [`../2-process/run-logs/`](../2-process/run-logs/).

## Achieved — measured in this proof of concept

| Result | Number | Source |
|---|---|---|
| Automated tests passing | **128 / 128** — run against the real database, not mocks | [`pytest-summary.txt`](../2-process/run-logs/pytest-summary.txt) |
| Invoices loaded by ingestion | **88 / 92** (plain SQL load: 86 / 92) — fuzzy vendor matching recovered 2 | [`06-python/README.md`](../../06-python/README.md) |
| Bank lines matched automatically | **68 / 78** — the other 10 are bank charges that need a manual journal | [`reconciliation-engine-results.md`](../../06-python/reconciliation-engine-results.md) |
| Intercompany matched automatically | **36 / 48** — all 12 unmatched carry a specific reason | same file |
| AP invoices matched to payments | **41 matched, 1 probable, 7 unmatched** (49) | same file |
| Rule findings | **47 across 5 rules** — 7 amount outliers, 5 duplicate invoices, 19 FX-conversion flags, 4 mis-mapped accounts, 12 intercompany with no counterpart | [`rule-findings.md`](../../08-accounting-automation/rule-findings.md) |
| Hard accounting rules | Debit = credit and maker ≠ checker enforced **at the database level**, tested by trying to break them | [`05-sql/README.md`](../../05-sql/README.md) |

Which planted data problems were caught, and which were not: [seeded-issues-vs-detected.md](../1-data/seeded-issues-vs-detected.md).

## What the AI evaluation found — including the failure

The AI assistant's safety policy was evaluated on 11 hand-built cases with a **mock** model, so the numbers describe the
safety pipeline's behaviour, not a real model's accuracy
([`evaluation-results.md`](../../09-ai/evaluation-results.md)):

| Metric | Result |
|---|---|
| Classification accuracy | 64% (7 / 11) |
| Routed to human review | 73% (8 / 11) |
| False positives (flagged, but fine) | 5 / 11 |
| False negatives (auto-approved but **wrong**) | **1 / 11** |
| **Inappropriate automation rate** | **9% (1 / 11)** — the number that matters most |

Case `EVAL-010` passed every documented control and was still wrong. It was disclosed rather than tuned away; an
amount-outlier check and audit sampling were added in response
([`KNOWN_ISSUES.md` §3](../../KNOWN_ISSUES.md)). The real-model integration code is tested but was never exercised live in
this build.

## Target — not measured

Straight from the case study's status column:

| Metric | Current (fictional baseline) | Target | Status |
|---|---|---|---|
| Close duration | ~12 days | ≤ 7 days (R01) | **Target** — no real close cycle to time |
| Manual reconciliation | ~80% | ≤ 20% (R02) | **Target** |
| Intercompany exceptions | ~35 / month | ≤ 10 / month (R04) | **Target** |

## Live demo

The Close Control Centre runs against a live copy of the same synthetic dataset, no login:
[northstar-finance-os.streamlit.app](https://northstar-finance-os-bndfmftzjicmew2hvehcdx.streamlit.app/). Its metrics are
real queries and rule calls, covered by the 10 dashboard tests in the count above.

## Limits of this evidence

- Everything is synthetic, at a deliberately readable scale (a few hundred rows over three close periods).
- "Caught" means caught against a **planted** answer key; it says nothing about performance on real, unplanned errors.
- Full list of known bugs, assumptions and scope boundaries: [`KNOWN_ISSUES.md`](../../KNOWN_ISSUES.md).
