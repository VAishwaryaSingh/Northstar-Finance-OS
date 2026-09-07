# Demo Flow — Technical Run-of-Show

The logistics companion to [demo-script.md](./demo-script.md) — what to have open, in what order, and how to reset if something goes wrong mid-demo. Written so someone other than the person who built this could actually run the demo from this document alone.

## Before the room

```bash
# 1. Database up and seeded (only needed once per environment, not per demo)
sudo service postgresql start
psql -d northstar -c "SELECT COUNT(*) FROM invoices;"   # sanity check: should return 88

# 2. Confirm the full pipeline still runs clean (catches any local drift before you're in front of a customer)
.venv/bin/pytest -q   # expect 128 passed

# 3. Start the dashboard in a separate terminal, ahead of time -- don't start it live
.venv/bin/streamlit run 10-dashboard/app.py
# leave this running; the demo just switches to this browser tab at 7:00

# 4. Start the API in another terminal, ahead of time
.venv/bin/uvicorn main:app --app-dir 07-api
# leave this running; Swagger UI at http://localhost:8000/docs
```

## Tabs/windows to have open, in the order the demo uses them

| Time | What's open | Why prepared in advance |
|---|---|---|
| 1:00 | `02-process-mapping/current-state.md` (rendered, not raw markdown) | The ASCII diagram needs a monospace view to read cleanly |
| 2:00 | `03-architecture/system-architecture.md` | Same — the diagram is ASCII |
| 3:00 | `04-data/invoices.csv` open in a spreadsheet app, scrolled to a `vendor_name_raw` mismatch row | Don't hunt for the row live — know which row number in advance |
| 3:00 | A terminal ready to run `06-python/ingestion.py`, or `06-python/exception-report.md` already open | Running it live takes ~2 seconds and is a nice "it's really executing" moment, but have the report open as a fallback |
| 4:00 | Swagger UI (`http://localhost:8000/docs`), `POST /invoices` expanded | Pre-fill the request body so you're not typing JSON live |
| 5:00 | `08-accounting-automation/rule-findings.md`, scrolled to "Incorrect Account Mapping" | |
| 6:00 | `09-ai/evaluation-results.md` and `09-ai/evaluation.md` | Know exactly which row is the honest "wasn't caught" case before you're on stage — don't search for it live |
| 7:00 | Browser tab already on `localhost:8501` (the dashboard) | Switch tabs, don't restart Streamlit live |
| 9:30 | `12-implementation/rollout-plan.md`'s schedule table | |

## If something breaks mid-demo

- **Database connection drops:** `sudo service postgresql start`, then re-run whichever query failed. The dashboard and API both reconnect on next page load/request — no restart needed.
- **A live command doesn't behave as expected:** every `[SHOW: run ...]` cue in demo-script.md has a static fallback (a `.md` report file already generated) — switch to that and keep talking. The point being demonstrated is the same either way.
- **Someone asks to see something not on the script:** this repository's README.md links every phase's own README/controls.md — it's fine to say "let me pull that up" and navigate live; everything referenced in the demo script is real and running, not staged for exactly these five things.

## Timing discipline

10 minutes is tight for the amount of ground [demo-script.md](./demo-script.md) covers. If running long, the two sections safest to compress are **1:00–2:00 (Discovery recap)** — the audience already lived this, so a faster recap lands fine — and **9:30–10:00 (Implementation)** — this is what [12-implementation/](../12-implementation/) exists to cover in writing afterward, not something that needs full live detail. Do not compress **5:00–7:00 (Accounting automation)** — the AI trust section is the one most likely to be challenged, so it needs its full time and the honest "wasn't caught" moment specifically, not just the confident parts.
