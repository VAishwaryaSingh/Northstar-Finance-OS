# Close Control Centre — Northstar Finance OS

A CFO/Controller-facing dashboard implementing PLAN.md §27 — the nine metrics it asks for, all computed live against the real database.

## Run it

```bash
.venv/bin/streamlit run 10-dashboard/app.py
```

Opens at `http://localhost:8501`. Needs the `northstar` PostgreSQL database from Phase 8 with data loaded (Phases 7–13).

```bash
.venv/bin/pytest 10-dashboard/tests -v   # 10 tests, against the real database (read-only)
```

## Files

| File | Purpose |
|---|---|
| `data.py` | Every metric as a plain, Streamlit-free function — SQL for aggregations, direct calls into `08-accounting-automation`'s rule functions for the two that are genuine rule logic (see `dashboard-spec.md`) |
| `app.py` | Thin Streamlit rendering layer over `data.py` — KPI cards, then a table per metric |
| `db.py` | Same connection helper pattern as every other phase |
| `dashboard-spec.md` | The nine metrics, where each comes from, and the design reasoning |
| `tests/` | 10 pytest tests against the real database |

## What it actually found, last run

| Metric | Result |
|---|---|
| Close progress | 79.5% (35/44 journal entries posted) |
| Manual journal % | 72.7% (32/44) |
| Unapproved journals | 9 |
| Overdue AP | 6 |
| Outstanding reconciliations | 22 (10 bank + 12 intercompany) |
| AI recommendations awaiting review | 4 — the same 4 "incorrect account mapping" invoices Phase 11's `run_rules.py` already found |
| Data-quality exceptions | 17 (5 duplicate invoices, 12 intercompany without a counterpart) |

Every number here matches what earlier phases independently found — a real cross-check, not a coincidence, since `data.py` calls the actual same rule functions and equivalent SQL patterns those phases already proved.

## A real bug this phase found and fixed

`get_data_quality_exceptions`'s first version queried `invoices` without selecting `invoice_date`, `currency`, or `amount` — three of the five fields `check_required_fields` checks. Every one of the 88 real invoices came back "missing" those three fields, producing 264 false positives out of 281 total findings. Caught by actually running it against the database rather than trusting the code, fixed by adding the missing columns to the query, and covered by a permanent regression test (`test_data_quality_exceptions_has_no_false_missing_field_hits`).

## Known limitations

See `dashboard-spec.md`'s "Known limitations" — no caching/auto-refresh, no dashboard-level authentication (matches this project's stated portfolio-POC security scope), and the overdue-AP reference date is a fixed constant, not `date.today()`, since this is a fictional dataset anchored to its own timeline.
