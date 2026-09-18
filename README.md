# Northstar Finance OS

**End-to-end finance transformation / AI-native ERP portfolio proof of concept**

> Northstar Finance OS is an end-to-end finance transformation proof of concept for a fictional multi-entity healthcare group. It demonstrates how accounting process discovery can be translated into finance-system architecture, SQL data modelling, Python automation, REST API integration, reconciliation, AI-assisted accounting workflows and implementation planning.

**Everything in this project — the client, entities, and data — is fictional.** This is a portfolio project, not production software, and was never built for or with a real company's data. See "What's fictional vs. actually implemented" below for exactly where that line sits.

**🔴 Live dashboard:** [northstar-finance-os.streamlit.app](https://northstar-finance-os-bndfmftzjicmew2hvehcdx.streamlit.app/) — the real Close Control Centre from [10-dashboard/](./10-dashboard/), running against a live copy of the same synthetic dataset used throughout this repo. No login required.

---

## What is this?

A hands-on demonstration of end-to-end finance-transformation capability: discovery → requirements → target architecture → data model → SQL → Python data pipeline → REST API → deterministic accounting automation → an AI-assisted accounting workflow with human controls → a live reporting dashboard → an implementation/migration plan → a solutions-consulting demo. Every one of those isn't a description — it's a working, tested deliverable in this repository, with its own README and test suite.

## What does it demonstrate?

The combination of deep accounting domain knowledge — multi-entity accounting, R2R/P2P/O2C, close, reconciliations, ICFR/PCAOB controls — with hands-on technical capability in the systems finance transformation actually runs on.

## What business problem does it solve?

Northstar Health Group's close takes ~12 business days, ~70% of journals are manual, bank reconciliation is ~80% manual, intercompany carries ~35 unresolved exceptions/month, and management reporting takes ~2 days to assemble by hand — because every handoff between billing, banking, AP, and the ERP is manual and unvalidated, with problems caught downstream instead of at the point data enters the system. Full discovery: [01-discovery/](./01-discovery/).

## What did I build?

| Layer | Where | What |
|---|---|---|
| Discovery & process mapping | [01-discovery/](./01-discovery/), [02-process-mapping/](./02-process-mapping/) | Stakeholder discovery, prioritised requirements (R01-R12), current/future-state process maps |
| Architecture | [03-architecture/](./03-architecture/), [ADRs/](./ADRs/) | Six-layer target architecture, data model, security model, 4 architecture decision records |
| Data & SQL | [04-data/](./04-data/), [05-sql/](./05-sql/) | Deterministic synthetic dataset (deliberately messy, ground-truth logged), 14-table PostgreSQL schema with real database-enforced controls, six SQL query sets |
| Python pipeline | [06-python/](./06-python/) | Ingestion (validation → dedup → mapping → normalisation → load), a dedicated four-tier reconciliation engine |
| REST API | [07-api/](./07-api/) | FastAPI integration surface — customers, invoices, payments, journal entries, reporting — with idempotent posting and structured error handling |
| Accounting automation | [08-accounting-automation/](./08-accounting-automation/) | Deterministic rules: vendor→account mapping, FX requirement, duplicate/missing-field detection, approval workflow |
| AI assistant | [09-ai/](./09-ai/) | A Claude-based accounting assistant with a tested safety policy — confidence threshold, no-hallucinated-data check, mandatory-reason overrides — evaluated honestly, including a disclosed gap |
| Dashboard | [10-dashboard/](./10-dashboard/) — [**live demo**](https://northstar-finance-os-bndfmftzjicmew2hvehcdx.streamlit.app/) | A live Streamlit Close Control Centre — every metric a real query or rule against the actual database |
| Implementation planning | [12-implementation/](./12-implementation/) | A 9-phase implementation plan, migration plan, rollout plan, risk register, training plan |
| Solutions demo | [11-demo/](./11-demo/) | A timed 10-minute demo script and the discovery-to-solution narrative connecting all of it |
| Portfolio | [13-case-study/](./13-case-study/) | Case study, executive summary |

**128 automated tests, all passing**, run against real (if synthetic) data throughout — not mocked.

## What technologies were used?

PostgreSQL 15 · Python (pandas, SQLAlchemy, Pydantic, pytest) · FastAPI · Streamlit · the Anthropic API (Claude Haiku 4.5 — integration code is real and tested, but never exercised live in this build; see [09-ai/README.md](./09-ai/README.md) for why). Nothing here is listed because it sounds good — every technology named has a corresponding working, tested deliverable.

## What's fictional vs. actually implemented?

**Fictional:** the client (Northstar Health Group), all entities/customers/vendors/transactions (synthetic, deterministically generated — [04-data/generate_data.py](./04-data/generate_data.py)), the discovery stakeholder interviews (a simulated script, not a real client engagement), and every business outcome labelled **Target** rather than **Achieved** in [13-case-study/case-study.md](./13-case-study/case-study.md) — this POC has no real close cycle to measure a 12-day-to-7-day improvement against.

**Actually implemented and tested:** the schema and its database-enforced constraints, the Python pipeline, the REST API, the deterministic accounting rules, the AI safety policy (with a real, disclosed evaluation gap — not a claimed clean pass), the reconciliation engine, and the dashboard. Every one of these has its own test suite and was run against real (if synthetic) data, not just written and reviewed.

## How do I run it?

```bash
# Database (PostgreSQL 15)
sudo service postgresql start
psql -d northstar -f 05-sql/schema.sql
psql -d northstar -f 05-sql/seed.sql

# Python environment
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Full test suite (128 tests)
.venv/bin/pytest

# Individual phases (see each folder's own README for detail)
.venv/bin/python 06-python/ingestion.py
.venv/bin/uvicorn main:app --app-dir 07-api
.venv/bin/streamlit run 10-dashboard/app.py
```

Full setup detail lives in each phase's own `README.md` — [05-sql/README.md](./05-sql/README.md), [06-python/README.md](./06-python/README.md), [07-api/README.md](./07-api/README.md), [09-ai/README.md](./09-ai/README.md), [10-dashboard/README.md](./10-dashboard/README.md).

## Where is the architecture?

[03-architecture/system-architecture.md](./03-architecture/system-architecture.md) — the six-layer design (Sources → Integration → Core → AI → Controls → Outputs), plus [data-model.md](./03-architecture/data-model.md), [integration-map.md](./03-architecture/integration-map.md), [security-model.md](./03-architecture/security-model.md), and the [ADRs/](./ADRs/) behind the key decisions (why PostgreSQL, why deterministic rules before AI, why retain the legacy ERP initially, and more).

## Where is the demo?

[11-demo/demo-script.md](./11-demo/demo-script.md) — a timed 10-minute walkthrough where every "show this" cue points at a real, working artifact already in this repository, not a mockup. [11-demo/discovery-demo.md](./11-demo/discovery-demo.md) has the full "you told me X → we found Y → we designed Z" narrative behind it.

## Where is the evidence?

[evidence/](./evidence/) — a guided path through the underlying data, the process, and the outcome, with captured run logs and a check of every planted data issue against what the system actually caught.

## What did I learn?

Full discussion in [13-case-study/case-study.md](./13-case-study/case-study.md)'s Lessons section. The short version: two real bugs were found only by running code against real data, not by review alone; the highest-leverage design decision (validate once, at ingestion, not repeatedly downstream) was architectural, made before any code existed; and the most valuable AI-safety result wasn't a clean evaluation pass — it was finding, and disclosing, a specific case that passed every documented control and was still wrong.

## What are the known bugs and limitations?

**[KNOWN_ISSUES.md](./KNOWN_ISSUES.md)** — every real bug found and fixed during development (with root cause and fix), the AI evaluation's disclosed gap, every documented assumption not yet confirmed with a real client, every integration not yet wired end-to-end, and every deliberate scope boundary. One page, instead of the eleven different `README.md`/`controls.md` files each item is also discussed in.

---

## Project structure and status

Full specification and build sequence: [PLAN.md](./PLAN.md) — its `STATUS` block at the top is the single source of truth for current progress. Working context for AI coding tools: [AGENTS.md](./AGENTS.md).
