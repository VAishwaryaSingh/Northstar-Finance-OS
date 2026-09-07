# Dashboard Spec — Close Control Centre (Phase 14, PLAN.md §27)

## The nine metrics PLAN.md §27 asks for, and where each comes from

| Metric | Function (`data.py`) | Source |
|---|---|---|
| Close progress | `get_close_progress` | SQL — journal_entries posted vs. total, by entity/period |
| Outstanding reconciliations | `get_outstanding_reconciliations` | SQL — bank + intercompany rows not `match_status = 'matched'` |
| Unreconciled cash | `get_unreconciled_cash` | SQL — the actual £/$ amount unreconciled, by entity/currency, not just a count |
| Unapproved journals | `get_unapproved_journals` | SQL — journal_entries where `status <> 'posted'`, with amount |
| Intercompany exceptions | `get_intercompany_exceptions` | SQL — intercompany_transactions where `match_status <> 'matched'` |
| Overdue AP | `get_overdue_ap` | SQL — unpaid AP invoices past due_date, relative to a fixed reference date (2026-09-07, matching `05-sql/ap.sql`) |
| Manual journal percentage | `get_manual_journal_pct` | SQL — `journal_entries.source = 'manual'` vs. total |
| AI recommendations awaiting review | `get_ai_recommendations_awaiting_review` | **Live rule**, not SQL — calls `08-accounting-automation/invoice_classification.classify_vendor_account` against every real AP invoice |
| Data-quality exceptions | `get_data_quality_exceptions` | **Live rules**, not SQL — calls three of `08-accounting-automation/exception_rules.py`'s functions against real data |

## Why two of these call Python rules instead of writing SQL

Every other metric here is a straightforward aggregation query, and matches the pattern already proven in `05-sql/` and `07-api/models.py`. The last two are different: "which invoices need AI-assisted review" and "what data-quality problems exist right now" are genuine rule *logic* (a vendor/account mismatch, a duplicate-key check, a missing-field check), already written, tested, and proven against real data in Phase 11 (`08-accounting-automation/`). Reimplementing that logic a third time in raw SQL here would risk it quietly drifting from what Phase 11 and Phase 12 actually check — the same reasoning `09-ai/controls.md` gives for why the AI assistant calls into Phase 11's rules directly rather than duplicating them. The dashboard should show what the rules that actually govern this project's data actually find, not a fourth independent opinion.

## Design choices

- **A thin app.py over a plain data.py.** Every metric function takes a database connection and returns a DataFrame or dict — no Streamlit import in `data.py` at all. This is what makes "the repository should retain reproducible data and queries" (PLAN.md §27) actually true: any of these can be run from a plain Python REPL, a notebook, or a different dashboard tool entirely, not just from inside a running Streamlit session.
- **Streamlit, not Power BI.** PLAN.md §27 allows either; Streamlit was already in `requirements.txt` from the initial repo scaffold and needs no license, desktop install, or `.pbix` file to review — a plain-text, version-controlled `app.py` a reviewer can read directly is a better fit for a portfolio repository than a binary Power BI file.
- **Live queries, not a cached snapshot.** Every number is computed on each page load against the current database state — there's no intermediate "last refreshed at" staleness to reason about, and running `04-data/generate_data.py` + reloading changes what the dashboard shows on the next refresh, with no separate ETL step to remember to run.

## Verification

`app.py` was run through Streamlit's own headless `AppTest` framework (`streamlit.testing.v1.AppTest`), which actually executes the script server-side rather than just checking that a static HTML shell loads — confirmed zero exceptions, all 5 KPI cards and all 8 tables render, against the real database. `data.py`'s 10 pytest tests (including a regression test for a real bug found while building this — see README.md) cover each metric function independently. See README.md for the exact numbers from the last verified run.

## Known limitations

- No auto-refresh / caching strategy — every page load re-runs every query and every rule live. Fine at this dataset's size (a few hundred rows); a production version would want `st.cache_data` with a sensible TTL.
- No authentication on the dashboard itself — anyone who can reach the Streamlit process can view it. Matches this project's stated portfolio-POC security scope (`03-architecture/security-model.md`), not a gap unique to this phase.
- `REFERENCE_DATE` (used for overdue-AP calculations) is a fixed constant, matching `05-sql/ap.sql`'s convention, rather than `date.today()` — this is a fictional dataset anchored to a specific point in its own timeline, not a live production system.
