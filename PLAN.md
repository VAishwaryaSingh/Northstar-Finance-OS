# Northstar Finance OS — End-to-End Accounting AI / ERP Portfolio Project

```text
STATUS: Phase 12 complete (Milestone 7 — AI) — starting Phase 13 (Reconciliation Engine)
LAST UPDATED: 2026-09-07

COMPLETED:
- Repository folder structure created (01-discovery ... 13-case-study, ADRs)
- AGENTS.md, .gitignore, .env.example, requirements.txt, pyproject.toml, LICENSE, README added
- Phase 1 (Discovery): 01-discovery/discovery-script.md, stakeholder-map.md, discovery-notes.md
- Phase 2 (Requirements): 01-discovery/requirements.md (R01-R12)
- Phase 3 (Current-state process): 02-process-mapping/current-state.md
- Phase 4 (Future-state process): 02-process-mapping/future-state.md, process-analysis.md
- Phase 5 (Target architecture): 03-architecture/system-architecture.md, integration-map.md, security-model.md; ADRs/0001-0004 (PostgreSQL, API+CSV ingestion, deterministic-rules-before-AI, retain-legacy-ERP-initially)
- Phase 6 (Data model): 03-architecture/data-model.md — logical schema for all 14 tables (entities, users, chart_of_accounts, customers, vendors, invoices, payments, bank_transactions, journal_entries, journal_lines, intercompany_transactions, fx_rates, approvals, audit_logs), with debit=credit and maker≠checker enforced as documented constraints and every table traced to R01-R12
- Phase 7 (Synthetic data): 04-data/generate_data.py (deterministic, seed=42) generating entities/chart_of_accounts/customers/vendors/fx_rates/invoices/payments/bank_transactions/journal_entries/journal_lines/intercompany_transactions.csv, plus README.md and an auto-generated data-quality-log.md (65 planted issues across 9 categories, verified: every journal entry balances, no journal is self-approved)
- Phase 8 (SQL): PostgreSQL 15 installed and running locally; 05-sql/schema.sql (all 14 tables, debit=credit enforced via a deferred trigger, maker≠checker enforced via a CHECK + trigger — both proven by deliberately trying to break them), seed.sql (loads 04-data/*.csv, 86/92 invoices load cleanly, 6 excluded exactly matching the planted missing-entity-code/unmapped-vendor issues), and ap.sql/reconciliation.sql/intercompany.sql/close_analysis.sql/reporting.sql/controls.sql (PLAN.md §20's six query categories). Full pipeline (drop db → schema → seed → all six query files) re-run clean from scratch with zero errors before commit.
- Phase 9 (Python data pipeline): .venv set up with pandas/pydantic/sqlalchemy/psycopg2/pytest; 06-python/{db,mappings,validation,transformations,reconciliation,ingestion}.py implementing PLAN.md §21's full pipeline (read → schema validation → data-quality checks → duplicate detection → entity/account mapping → currency normalisation → DB load → reconciliation → exception report) for invoices/payments/bank_transactions/intercompany_transactions. 26 pytest tests (mapping, currency conversion, duplicate detection, reconciliation — the four AGENTS.md calls out) all passing. Run against the real database: recovers 88/92 invoices (vs seed.sql's 86) via fuzzy vendor-name matching, flags 5 duplicate invoices at load time, independently re-derives bank/intercompany matches rather than trusting source labels. Two real bugs found and fixed by actually running it (NaN-vs-None handling in two places) — see 06-python/README.md. exception-report.md regenerated and cross-checked against 04-data/data-quality-log.md.
- Phase 10 (REST API): 07-api/ (FastAPI) — main.py, config.py, auth.py, errors.py, db.py, models.py (SQLAlchemy Core data-access layer), schemas.py (Pydantic request/response models), routes/{customers,invoices,payments,journal_entries,reporting}.py. Implements POST /customers, /invoices, /payments, /journal-entries and GET /trial-balance, /reconciliation-status, /close-status, /intercompany-exceptions per PLAN.md §22. Demonstrates all six things §22 asks for: request validation, response schemas, structured errors with real HTTP status codes (404/400/422), a basic X-API-Key auth concept, idempotent invoice creation (replay-safe on entity_code+invoice_number+invoice_type, flags a same-number/different-amount replay as duplicate_flagged rather than silently posting it), and request logging. Balance/maker≠checker validated client-side (422, schemas.py) *and* by schema.sql's trigger/constraint (400, IntegrityError handler) as the real source of truth. Manually smoke-tested live via curl (auth rejection, validation errors, idempotency replay, unbalanced/self-approved journal rejection, filtered GET queries) before writing the automated suite; 27 pytest tests via FastAPI's TestClient against the real database, each using a disposable per-test entity_code so nothing touches the seeded dataset. Full suite (06-python + 07-api) = 53/53 passing.
- Phase 11 (Accounting automation): 08-accounting-automation/{invoice_classification,exception_rules,journal_workflow}.py per PLAN.md §23 — vendor→account mapping (flag, don't silently correct, a mismatch), entity→ledger validation, currency→FX requirement, duplicate invoice/missing-required-field/intercompany-counterpart exceptions, and the amount→approval-threshold rule (10,000, documented assumption, formalises 05-sql/controls.sql's placeholder) driving determine_journal_status. 24 pytest tests, all pure-function/no-DB. run_rules.py proves every rule against the real database (rule-findings.md): 5 duplicate invoices and 4 incorrect account mappings (both matching known counts, with the same "excluded earlier for a different reason" edge case documented in 06-python/README.md), 12 unmatched intercompany transactions, and — a genuinely new finding, not just a re-check — 19 intercompany transactions crossing a currency boundary given the one-USD/two-GBP entity mix. controls.md documents the critical rules-before-AI distinction this phase exists to protect going into Phase 12. Full suite (06-python + 07-api + 08-accounting-automation) = 77/77 passing.
- Phase 12 (AI accounting assistant): 09-ai/{llm_client,accounting_agent}.py per PLAN.md §24-25. Built and evaluated fully offline by explicit user choice (no ANTHROPIC_API_KEY configured) — MockLLMClient is a deterministic stub used by every test/eval; AnthropicLLMClient is a real, correct implementation (Claude Haiku 4.5, strict schema-validated tool use) that was never exercised, documented as the go-live path in README.md. process_invoice() calls directly into 08-accounting-automation's classify_vendor_account and approval_requirement (not reimplementations — the AI must be checked by the one real rule engine, per controls.md). Implements every PLAN.md §25 requirement. 13 pytest tests covering all six PLAN.md §30 AI test categories. evaluate.py + 10 hand-built examples/*.json produced evaluation-results.md: 60% classification accuracy, 70% routed to human review, 10% inappropriate automation rate (1/10 — EVAL-010, a deliberately-constructed case where every check passes but the ground truth is still wrong, documented as an honest residual-risk finding, not a bug).
- Phase 12 follow-up (user-requested): asked "can we add a check for this and fix it" re: EVAL-010. Answered honestly first (no per-transaction rule can close a gap for a transaction indistinguishable from normal on every observable signal), then added two general, non-curve-fitted controls to 08-accounting-automation: invoice_classification.check_amount_outlier (flags a vendor's invoice amount as a statistical outlier against their own history) and exception_rules.should_sample_for_audit (deterministic-per-ID random sampling of even fully-clean auto-approved transactions, the real industry answer to the residual category no rule can close). Wired into 09-ai's process_invoice as steps 5-6. New EVAL-011 case proves check_amount_outlier catches a real, different failure mode; EVAL-010 was re-run honestly afterward and was NOT caught this run (not selected by the 5% audit sample) -- reported as-is in evaluation.md, not re-rolled to force a pass. check_amount_outlier additionally run against the real database via run_rules.py (leave-one-out per AP vendor): found 7 real outliers among 49 AP invoices, with an honest caveat that this dataset's uniformly-random synthetic amounts and small per-vendor sample sizes inflate that rate versus a realistic deployment. 14 new tests added (10 in 08-accounting-automation, 4 in 09-ai). Full project suite = 104/104 passing.

IN PROGRESS:
- (none)

NEXT:
- Phase 13: Reconciliation Engine — 05-sql or a dedicated module per PLAN.md §26: bank matching (amount/date/reference/counterparty), AP matching (invoice/payment/vendor/amount), intercompany matching (source entity/counterparty entity/reference/amount/currency/period), each outputting matched/probable-match/unmatched/exception-reason. Builds on (doesn't replace) the matching logic already in 06-python/reconciliation.py and 08-accounting-automation/exception_rules.py.

BLOCKERS:
- (none)

KNOWN LIMITATIONS:
- No real LLM call has been made anywhere in this project — 09-ai/llm_client.py's AnthropicLLMClient is real, correct code, but untested without an API key (the user's explicit choice for this phase). evaluation-results.md's numbers describe the safety-policy pipeline given MockLLMClient's canned responses, not real model accuracy.
- 09-ai's audit log (OverrideRecord) isn't wired into schema.sql's audit_logs table yet, and neither 08-accounting-automation's nor 09-ai's rules are wired into 07-api yet. Natural next integration steps, deliberately not done to keep each phase reviewable on its own (see each phase's controls.md).
- The 10,000 approval threshold (08-accounting-automation/journal_workflow.py, reused by 09-ai) is still a documented assumption, not a real Northstar Health Group policy.
- 07-api's authentication is a single shared key, not per-user identity/roles — matches security-model.md's stated scope for this portfolio project. No pagination on GET endpoints. POST /invoices and /payments expect a vendor_code/customer_code that already exists (no fuzzy matching at the API layer — that's 06-python's job for messy source files, not an API caller's).
- current-state.png / future-state.png / system-architecture.png diagrams not yet drawn — ASCII flow diagrams stand in for now.
- NOTE ON PHASE NUMBERING: PLAN.md's own §-numbered phases (used in this STATUS block) are the authoritative sequence going forward — Phase 9=Python pipeline (§21), Phase 10=REST API (§22), Phase 11=Accounting automation (§23), Phase 12=AI assistant (§24), Phase 13=Reconciliation Engine (§26), Phase 14=Close Control Centre (§27). The early saved roadmap plan (~/.claude/plans/groovy-discovering-pinwheel.md) numbered these slightly differently (its "Step 10" was Reconciliation Engine, "Step 11" REST API) — that roadmap file is now superseded by this STATUS block where they conflict.

CURRENT TECH STACK:
- Python (pandas, pydantic, sqlalchemy, psycopg2, pytest, fastapi, uvicorn, httpx, anthropic) in a project .venv. PostgreSQL 15 (installed and running locally). Streamlit — not yet implemented. anthropic SDK installed and integration code written (09-ai/llm_client.py), but no API key configured and no live call made.

LAST VERIFIED:
- Tests: 06-python/tests + 07-api/tests + 08-accounting-automation/tests + 09-ai/tests — 104/104 passing (.venv/bin/pytest, using pyproject.toml's testpaths)
- API: 07-api/main.py — manually smoke-tested live (uvicorn + curl) and covered by 27 automated tests against the real database
- Database: PostgreSQL 15 local — schema, seed, all six SQL query sets, the Python ingestion pipeline, the REST API, and the accounting-automation rules all run clean end-to-end
- Dashboard: n/a
```

## 0. PROJECT PURPOSE

This document is the complete project specification and handoff context for building a portfolio project designed to demonstrate practical capability for London accounting-AI, AI-native ERP, finance transformation, accounting solutions, deployment, implementation, and solutions-consulting roles.

The project is deliberately designed around the gap between:

- strong accounting / audit / controls knowledge, and
- limited direct production experience with ERP implementation, SQL, APIs, data migration, and formal solutions consulting / product demonstrations.

The goal is NOT to pretend that production implementation experience exists.

The goal is to build a credible, technically grounded, end-to-end proof-of-work project showing that the candidate can:
1. understand accounting operations deeply;
2. discover and document finance-system problems;
3. translate accounting workflows into system requirements;
4. design a target-state finance architecture;
5. work with structured accounting data;
6. use SQL for finance analysis;
7. build a Python-based ingestion / validation / reconciliation pipeline;
8. expose and consume REST APIs;
9. model ERP-style workflows;
10. design AI-assisted accounting workflows responsibly;
11. build controls, auditability and human-in-the-loop approval;
12. create implementation / migration plans;
13. communicate a solution to CFO / Controller stakeholders;
14. explain technical trade-offs to engineers;
15. produce a polished portfolio case study and demo.

This is a portfolio / proof-of-concept project. It must never be represented as a production implementation or as work performed for a real company.

---

# 3. PROJECT NAME

## Northstar Finance OS

### Subtitle

**AI-Native ERP & Month-End Close Implementation POC**

Alternative portfolio title:

**Northstar Finance OS — End-to-End Finance Systems Transformation POC**

Recommended title for GitHub:

`northstar-finance-os`

Recommended repo description:

> End-to-end finance transformation POC for a fictional multi-entity healthcare group: accounting process discovery, ERP architecture, SQL data model, Python ETL, reconciliation, REST API integration, AI-assisted accounting workflow, controls, implementation roadmap and CFO demo.

---

# 4. FICTIONAL CLIENT

## Northstar Health Group

A fictional UK/US healthcare group.

The fictional nature must be explicit in the README and portfolio.

### Group structure

Three entities:

1. Northstar Health Holdings Ltd — UK
2. Northstar Health Services Inc — US
3. Northstar Shared Services Ltd — UK

### Currencies

- GBP
- USD

### Approximate transaction volume

~5,000 transactions per month.

This is synthetic and intentionally chosen for a portfolio-scale POC.

---

# 5. CURRENT-STATE BUSINESS ENVIRONMENT

Northstar currently operates with:

- legacy ERP
- billing platform
- bank CSV exports
- AP invoice files
- Excel reconciliation workbooks
- Excel reporting packs
- PowerPoint management reporting

The current environment contains fragmented data and substantial manual intervention.

## Current close profile

Use these as fictional baseline assumptions:

| Metric | Current State |
|---|---:|
| Month-end close | 12 business days |
| Manual reconciliations | 80% |
| Manual journal preparation | 70% |
| Intercompany exceptions | 35/month |
| Reporting preparation | 2 days |
| Manual transaction imports | 100% for integrated-source data |

These are fictional baseline assumptions, not measured results from a real organisation.

---

# 6. TARGET-STATE BUSINESS OUTCOMES

Use these as target-state objectives, not guaranteed outcomes.

| Metric | Current | Target |
|---|---:|---:|
| Month-end close | 12 days | ≤7 days |
| Manual reconciliations | 80% | ≤20% |
| Manual journal preparation | 70% | ≤25% |
| Intercompany exceptions | 35/month | ≤10/month |
| Reporting preparation | 2 days | <4 hours |
| Manual imports from integrated sources | 100% | 0% |

The final project should explain how the proposed system could contribute to these outcomes.

Do NOT claim the POC itself achieved them unless an actual test demonstrates it.

---

# 7. CORE BUSINESS PROBLEMS

The fictional CFO / Controller has identified:

1. Month-end close takes too long.
2. Reconciliations are heavily spreadsheet-driven.
3. Billing data must be manually transferred into the ERP.
4. Intercompany transactions frequently fail to match.
5. Management reporting requires manual preparation.
6. Data-quality issues are discovered late.
7. Multi-entity and multi-currency accounting increases complexity.
8. Controls and auditability are concerns when automating accounting.
9. Finance users spend too much time on data movement rather than exception management.
10. Existing systems may be technically capable but require substantial manual orchestration.

---

# 8. PROJECT SUCCESS CRITERIA

By completion, the portfolio should demonstrate all of the following.

## Accounting

- Understand the accounting workflow end to end.
- Model entities, accounts, invoices, payments, journals and intercompany transactions.
- Explain close, reconciliation and reporting processes.
- Demonstrate accounting controls.

## Process consulting

- Run a simulated discovery process.
- Document current-state processes.
- Identify pain points and root causes.
- Convert pain points into requirements.
- Prioritise requirements.
- Define success metrics.

## Systems

- Create target-state architecture.
- Explain system boundaries.
- Explain data flows.
- Explain integration points.
- Explain migration approach.

## SQL

- Create relational schema.
- Load synthetic data.
- Query accounting data.
- Perform reconciliations.
- Produce finance analytics.

## Python

- Ingest source files.
- Validate data.
- detect duplicates.
- normalise currencies / fields.
- map accounts/entities.
- load data.
- produce reconciliation outputs.

## API

- Build or simulate a REST API.
- Demonstrate posting / retrieving accounting objects.
- Explain API concepts.
- Demonstrate authentication conceptually.
- Demonstrate error handling.
- Demonstrate idempotency conceptually or practically.

## AI

- Build AI-assisted classification / exception workflow.
- Include confidence score.
- Include reasoning / evidence.
- Include human review.
- Prevent uncontrolled posting.
- Log decisions.

## Controls

- Segregation of duties.
- Approval thresholds.
- Audit trail.
- Validation.
- Exception queues.
- Confidence thresholds.
- Human-in-the-loop.
- Role-based access concept.
- Data-quality controls.

## Solutions consulting

- Discovery questions.
- Client pain-point synthesis.
- Solution mapping.
- Tailored demo.
- Objection handling.
- Technical explanation.
- Executive communication.

---

# 9. PRINCIPLE: BUILD IN INCREASING TECHNICAL DEPTH

Do not start by coding an AI agent.

Build in this order:

1. Business problem
2. Discovery
3. Requirements
4. Current-state process
5. Target-state process
6. Architecture
7. Data model
8. Synthetic data
9. SQL
10. Python ETL
11. Reconciliation
12. API
13. Accounting automation
14. AI-assisted workflow
15. Controls
16. Dashboard
17. Demo
18. Case study

This sequence is important because the project should demonstrate systems thinking rather than “I built a chatbot.”

---

# 10. REPOSITORY STRUCTURE

Recommended structure:

```text
northstar-finance-os/
│
├── README.md
├── PLAN.md
├── LICENSE
├── .gitignore
├── requirements.txt
├── pyproject.toml
├── .env.example
│
├── 01-discovery/
│   ├── discovery-script.md
│   ├── discovery-notes.md
│   ├── stakeholder-map.md
│   └── requirements.md
│
├── 02-process-mapping/
│   ├── current-state.md
│   ├── future-state.md
│   ├── current-state.png
│   ├── future-state.png
│   └── process-analysis.md
│
├── 03-architecture/
│   ├── system-architecture.md
│   ├── system-architecture.png
│   ├── integration-map.md
│   └── security-model.md
│
├── 04-data/
│   ├── README.md
│   ├── generate_data.py
│   ├── entities.csv
│   ├── customers.csv
│   ├── vendors.csv
│   ├── chart_of_accounts.csv
│   ├── invoices.csv
│   ├── payments.csv
│   ├── bank_transactions.csv
│   ├── journal_entries.csv
│   ├── journal_lines.csv
│   ├── intercompany_transactions.csv
│   └── fx_rates.csv
│
├── 05-sql/
│   ├── schema.sql
│   ├── seed.sql
│   ├── reconciliation.sql
│   ├── close_analysis.sql
│   ├── intercompany.sql
│   └── reporting.sql
│
├── 06-python/
│   ├── ingestion.py
│   ├── validation.py
│   ├── transformations.py
│   ├── reconciliation.py
│   ├── mappings.py
│   └── tests/
│
├── 07-api/
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── routes/
│   │   ├── customers.py
│   │   ├── invoices.py
│   │   ├── payments.py
│   │   ├── journal_entries.py
│   │   └── reporting.py
│   └── tests/
│
├── 08-accounting-automation/
│   ├── invoice_classification.py
│   ├── journal_workflow.py
│   ├── exception_rules.py
│   └── controls.md
│
├── 09-ai/
│   ├── accounting_agent.py
│   ├── prompts.md
│   ├── evaluation.md
│   ├── controls.md
│   └── examples/
│
├── 10-dashboard/
│   ├── README.md
│   └── dashboard-spec.md
│
├── 11-demo/
│   ├── demo-script.md
│   ├── demo-flow.md
│   └── discovery-demo.md
│
├── 12-implementation/
│   ├── implementation-plan.md
│   ├── migration-plan.md
│   ├── rollout-plan.md
│   ├── risks.md
│   └── training-plan.md
│
└── 13-case-study/
    ├── case-study.md
    └── executive-summary.md
```

The exact structure may change as implementation progresses. AI coding tools are allowed to propose better structure, but changes must be documented in `PLAN.md` or an architecture decision record.

---

# 11. TOOLING STRATEGY

The user may use different AI coding tools during the project.

Possible tools include:

- ChatGPT
- Claude Code
- Cursor
- GitHub Copilot
- Windsurf
- Gemini
- other coding agents / IDE assistants

The project must remain tool-agnostic.

## Rule

AI coding tools are implementation assistants, not project owners.

The human must retain understanding of:

- why the architecture was chosen;
- what each component does;
- how data moves;
- what the accounting logic means;
- what controls exist;
- what assumptions were made;
- what was generated by AI;
- what was tested;
- what limitations remain.

## AI coding tool workflow

For every major task:

1. Give the AI tool the relevant project context.
2. Ask it to inspect existing files before modifying anything.
3. Ask it to propose a plan before large changes.
4. Review the plan.
5. Implement incrementally.
6. Run tests.
7. Inspect outputs.
8. Update documentation.
9. Commit the change.
10. Record major decisions.

Do not ask an AI coding tool to rewrite the entire repository unless there is a specific reason.

Prefer small, testable changes.

---

# 12. PROJECT CONTEXT FILE FOR AI CODING TOOLS

Create a root-level file:

`AGENTS.md`

This should contain:

- project purpose;
- fictional client details;
- architecture;
- coding conventions;
- accounting assumptions;
- testing requirements;
- security rules;
- no-real-data rule;
- no-secret rule;
- documentation requirements;
- definition of done;
- current project status.

For tools that support different context filenames, maintain equivalents only when necessary.

Examples:

- `AGENTS.md`
- `CLAUDE.md`
- `.cursor/rules/`
- `.github/copilot-instructions.md`

Do not create unnecessary duplicates.

The canonical source of project context should remain `PLAN.md` + `AGENTS.md`.

---

# 13. PHASE 1 — DISCOVERY

## Objective

Simulate a first customer discovery conversation with the CFO / Controller.

## Deliverables

`01-discovery/discovery-script.md`

Include questions covering:

### Business

- How long does close currently take?
- Which steps are most manual?
- Where do exceptions occur?
- Which processes are most painful?
- Which reports are most important to leadership?

### Accounting

- How are journals prepared?
- How are reconciliations performed?
- How are intercompany balances matched?
- How are approvals handled?
- How are multi-currency transactions managed?

### Systems

- What ERP is currently used?
- What billing systems feed accounting?
- How do banks connect?
- How are AP invoices received?
- Where are spreadsheets used?
- What systems own the source of truth?

### Data

- What data formats are available?
- How frequently are files / APIs updated?
- What identifiers exist?
- Are there duplicate records?
- How are entities / accounts mapped?

### Controls

- Who can create journals?
- Who approves journals?
- What approval thresholds exist?
- What evidence is retained?
- How are changes audited?

### Reporting

- What does the CFO need daily?
- What does the Controller need during close?
- Which reports are currently manual?

### Technology

- What integrations are available?
- Are APIs available?
- What data needs migration?
- What security requirements exist?
- What access controls are required?

## Output

Create a prioritised problem statement.

---

# 14. PHASE 2 — REQUIREMENTS

Create:

`01-discovery/requirements.md`

Use a table:

| ID | Problem | Requirement | Priority | Success Metric |
|---|---|---|---|---|
| R01 | Slow close | Automate close workflow | P0 | ≤7 days |
| R02 | Manual reconciliations | Automated reconciliation | P0 | ≤20% manual |
| R03 | Manual billing import | API / automated ingestion | P0 | 0% manual |
| R04 | IC mismatches | Automated matching | P0 | ≤10 exceptions/month |
| R05 | Manual reporting | Automated reporting layer | P1 | <4 hours |
| R06 | Control risk | Approval + audit trail | P0 | 100% journal traceability |
| R07 | Multi-entity complexity | Entity-aware accounting model | P0 | All entities supported |
| R08 | FX complexity | Currency + FX model | P1 | GBP/USD supported |

Expand this table during the project.

---

# 15. PHASE 3 — CURRENT-STATE PROCESS

Create:

`02-process-mapping/current-state.md`

Represent:

```text
Billing System
      ↓
CSV / Manual Export
      ↓
Excel
      ↓
Legacy ERP
      ↓
Finance Team
      ↓
Manual Reconciliation
      ↓
Manual Journals
      ↓
Intercompany Matching
      ↓
Reporting Workbook
      ↓
PowerPoint
      ↓
CFO
```

Include:

- process owner;
- system;
- input;
- output;
- manual step;
- control;
- failure mode;
- data quality issue;
- estimated effort.

---

# 16. PHASE 4 — FUTURE-STATE PROCESS

Design:

```text
Source Systems
 ├── Billing
 ├── Banking
 ├── AP
 └── Existing ERP
        ↓
Integration / Ingestion Layer
        ↓
Validation + Normalisation
        ↓
Finance Data Model
        ↓
Accounting Rules / AI Assistance
        ↓
Human Approval
        ↓
Journal / Subledger Posting
        ↓
Automated Reconciliation
        ↓
Close Control Centre
        ↓
CFO Reporting
```

Important:

AI should assist accounting decisions but must not bypass accounting controls.

---

# 17. PHASE 5 — TARGET ARCHITECTURE

Design a clear architecture diagram showing:

### Sources

- billing
- bank
- AP
- legacy ERP

### Integration

- API
- CSV ingestion
- validation
- transformation

### Core

- accounting data model
- journal engine
- reconciliation engine
- intercompany engine
- workflow engine

### AI

- classification
- exception explanation
- suggested accounting treatment
- anomaly detection

### Controls

- approvals
- role permissions
- audit logs
- confidence thresholds
- exception queues

### Outputs

- trial balance
- reconciliations
- close dashboard
- management reporting

---

# 18. PHASE 6 — DATA MODEL

Build a relational model containing at minimum:

- entities
- customers
- vendors
- chart_of_accounts
- invoices
- payments
- bank_transactions
- journal_entries
- journal_lines
- intercompany_transactions
- fx_rates
- users
- approvals
- audit_logs

## Key accounting principles

Journal entries should balance:

`Total Debits = Total Credits`

Every transaction should have:

- entity
- date
- currency
- source
- accounting classification
- status

Do not build a simplistic “AI says debit / credit” demo without modelling the underlying accounting objects.

---

# 19. PHASE 7 — SYNTHETIC DATA

Create realistic synthetic data.

Data should intentionally contain:

- duplicate invoices;
- missing entity codes;
- inconsistent vendor names;
- GBP transactions;
- USD transactions;
- unmatched bank transactions;
- unmatched intercompany transactions;
- incorrect account mappings;
- duplicate payments;
- missing invoice references;
- manual journal entries;
- late transactions.

The data should be messy enough to make the reconciliation and validation functionality meaningful.

Never use real customer or employer data.

---

# 20. PHASE 8 — SQL

Use PostgreSQL if practical.

SQLite is acceptable for the first iteration if environment constraints make PostgreSQL inconvenient, but PostgreSQL is preferable for demonstrating realistic relational database capability.

Create:

`05-sql/schema.sql`

Queries should include:

### AP

- unpaid invoices;
- overdue invoices;
- duplicate invoice candidates.

### Bank reconciliation

- unmatched bank transactions;
- matched transactions;
- reconciliation rate.

### Intercompany

- entity A vs entity B;
- amount differences;
- missing counterpart entries.

### Close

- journals posted by day;
- manual vs automated journals;
- outstanding close tasks.

### Reporting

- revenue by entity;
- expenses by entity;
- monthly movement;
- currency exposure.

### Controls

- journals without approval;
- journals above approval threshold;
- transactions missing required metadata.

---

# 21. PHASE 9 — PYTHON DATA PIPELINE

Create a Python ingestion pipeline:

```text
Source File
   ↓
Read
   ↓
Schema Validation
   ↓
Data Quality Checks
   ↓
Duplicate Detection
   ↓
Entity Mapping
   ↓
Account Mapping
   ↓
Currency Normalisation
   ↓
Database Load
   ↓
Reconciliation
   ↓
Exception Report
```

Use:

- pandas;
- SQLAlchemy;
- Pydantic where appropriate;
- pytest.

Avoid unnecessary frameworks.

The code should be readable by a finance professional learning engineering concepts.

---

# 22. PHASE 10 — REST API

Use FastAPI unless another framework has a strong reason.

Create endpoints such as:

```text
POST /customers
POST /invoices
POST /payments
POST /journal-entries

GET /trial-balance
GET /reconciliation-status
GET /close-status
GET /intercompany-exceptions
```

Demonstrate:

- request validation;
- response schemas;
- errors;
- HTTP status codes;
- basic authentication concept;
- idempotency for transaction posting if practical;
- logging.

The API should represent an ERP-style integration surface.

---

# 23. PHASE 11 — ACCOUNTING AUTOMATION

Before adding an AI agent, implement deterministic rules.

Examples:

- invoice vendor → default account mapping;
- entity → ledger mapping;
- currency → FX requirement;
- invoice amount → approval threshold;
- duplicate invoice → exception;
- missing tax field → exception;
- intercompany transaction → counterpart validation.

This distinction is critical:

**Rules should handle deterministic accounting controls. AI should assist with ambiguous classification / explanation / exception handling.**

---

# 24. PHASE 12 — AI ACCOUNTING ASSISTANT

Build an AI-assisted workflow.

Example:

```text
Invoice
   ↓
Extract fields
   ↓
Identify vendor
   ↓
Suggest entity
   ↓
Suggest account
   ↓
Suggest tax treatment
   ↓
Confidence score
   ↓
Evidence / reasoning
   ↓
Control checks
   ↓
Human approval
   ↓
Post
```

Example output:

```json
{
  "vendor": "Example Medical Supplies Ltd",
  "entity": "Northstar Health Holdings Ltd",
  "account": "Medical Supplies Expense",
  "currency": "GBP",
  "confidence": 0.94,
  "requires_human_review": false,
  "reason": "Vendor and historical invoice pattern match approved supplier mapping."
}
```

The exact output may differ.

---

# 25. AI SAFETY / CONTROL REQUIREMENTS

The AI must never silently post accounting entries without controls.

Implement or document:

- confidence threshold;
- human review;
- approval threshold;
- audit log;
- source evidence;
- deterministic validation;
- exception queue;
- segregation of duties;
- ability to override AI recommendation;
- reason for override;
- no hallucinated accounting data.

Example policy:

```text
Confidence >= 0.95
AND
all deterministic validation checks pass
AND
transaction below approval threshold
→ eligible for automated workflow

Otherwise
→ human review
```

Treat this as an illustrative policy, not a universal accounting rule.

---

# 26. PHASE 13 — RECONCILIATION ENGINE

Build a reconciliation process for:

### Bank

Match:

- amount;
- date;
- reference;
- counterparty.

### AP

Match:

- invoice;
- payment;
- vendor;
- amount.

### Intercompany

Match:

- source entity;
- counterparty entity;
- reference;
- amount;
- currency;
- period.

Output:

- matched;
- probable match;
- unmatched;
- exception reason.

---

# 27. PHASE 14 — CLOSE CONTROL CENTRE

Build a simple CFO / Controller dashboard.

Metrics:

- close progress;
- outstanding reconciliations;
- unreconciled cash;
- unapproved journals;
- intercompany exceptions;
- overdue AP;
- manual journal percentage;
- AI recommendations awaiting review;
- data-quality exceptions.

A simple Streamlit dashboard is acceptable.

Power BI is also acceptable if practical, but the repository should retain reproducible data and queries.

---

# 28. PHASE 15 — IMPLEMENTATION PLAN

Create:

`12-implementation/implementation-plan.md`

Structure:

## Phase 0 — Discovery

- stakeholders
- processes
- systems
- requirements

## Phase 1 — Design

- architecture
- data model
- controls
- integration design

## Phase 2 — Data preparation

- data inventory
- cleansing
- mapping
- validation

## Phase 3 — Integration

- API
- files
- banking
- billing

## Phase 4 — Configuration

- chart of accounts
- entities
- approval rules
- accounting rules

## Phase 5 — Testing

- unit testing
- integration testing
- reconciliation testing
- UAT
- controls testing

## Phase 6 — Migration

- historical data
- opening balances
- master data
- reconciliation

## Phase 7 — Pilot

- one entity
- limited process scope

## Phase 8 — Rollout

- remaining entities
- training
- support

---

# 29. MIGRATION PLAN

Document:

### Data inventory

What moves from legacy systems?

### Mapping

Legacy account → target account.

Legacy entity → target entity.

Legacy vendor → target vendor.

### Cleansing

- duplicates;
- invalid codes;
- missing fields;
- inactive suppliers.

### Validation

- record counts;
- balances;
- control totals;
- trial balance;
- reconciliation.

### Cutover

Define:

- freeze period;
- final extract;
- migration;
- validation;
- sign-off;
- go-live.

---

# 30. TESTING STRATEGY

Every meaningful component must have tests.

## Python

Test:

- duplicate detection;
- missing fields;
- currency conversion;
- mapping;
- reconciliation.

## API

Test:

- valid request;
- invalid request;
- duplicate posting;
- missing required fields;
- error responses.

## Accounting

Test:

- debit = credit;
- approval required;
- journal cannot post without required fields.

## AI

Test:

- high-confidence correct case;
- low-confidence case;
- ambiguous vendor;
- missing data;
- conflicting evidence;
- adversarial / nonsensical input.

---

# 31. AI EVALUATION

Do not say “the AI works” without evaluation.

Create a small evaluation dataset.

Measure:

- classification accuracy;
- false positives;
- false negatives;
- percentage routed to human review;
- inappropriate automation rate.

The most important metric is not simply model accuracy.

For an accounting workflow, also measure:

**unsafe automation rate**

i.e. how often the system would incorrectly allow a transaction through without required review.

---

# 32. SECURITY

Do not store:

- real API keys;
- passwords;
- real customer data;
- employer confidential information;
- personal financial information.

Use:

`.env.example`

with placeholders.

Document:

- authentication;
- authorisation;
- secrets management;
- least privilege;
- audit logging;
- sensitive data handling.

This is a portfolio POC, not a production-secure ERP.

State limitations clearly.

---

# 33. OBSERVABILITY

Where practical, log:

- ingestion status;
- validation failures;
- API requests;
- posting results;
- reconciliation status;
- AI recommendations;
- human overrides.

A simple structured log is sufficient.

---

# 34. SOLUTIONS-CONSULTING DEMO

This is one of the most important portfolio outputs.

Create a 10-minute demo.

## Recommended structure

### 0:00–1:00 — Customer problem

“You told me close takes 12 days and finance spends most of its time moving and reconciling data.”

### 1:00–2:00 — Discovery recap

Show:

- close;
- reconciliations;
- intercompany;
- reporting;
- controls.

### 2:00–3:00 — Architecture

Explain the flow.

### 3:00–5:00 — Data / integration

Show:

- source file;
- API;
- validation;
- database.

### 5:00–7:00 — Accounting automation

Show:

- invoice;
- classification;
- controls;
- human review.

### 7:00–8:30 — Reconciliation / close dashboard

Show:

- exceptions;
- close status;
- intercompany.

### 8:30–9:30 — CFO outcome

Connect the solution to:

- close time;
- manual work;
- visibility;
- controls.

### 9:30–10:00 — Implementation

Explain:

- pilot;
- migration;
- testing;
- rollout.

---

# 35. DISCOVERY-TO-DEMO STORY

The demo should not be:

> “Here are some cool features I built.”

It should be:

> “You told me X. We found Y. Therefore we designed Z. Here's how it solves the problem. Here's the control model. Here's how we'd implement it.”

This is what makes the project relevant to solutions consulting.

---

# 37. ARCHITECTURE DECISION RECORDS

Create:

`ADRs/`

For significant decisions.

Examples:

- Why PostgreSQL?
- Why FastAPI?
- Why Streamlit?
- Why deterministic rules before AI?
- Why human-in-the-loop?
- Why API + CSV ingestion?
- Why fictional data?
- Why retain legacy ERP initially?

Each ADR should contain:

```text
Decision
Context
Options considered
Decision
Trade-offs
Consequences
```

---

# 38. GIT WORKFLOW

Use meaningful commits.

Examples:

```text
feat: add Northstar discovery requirements
feat: add accounting relational schema
feat: generate synthetic finance dataset
feat: add bank reconciliation queries
feat: add Python ingestion pipeline
feat: add FastAPI invoice endpoint
feat: add intercompany matching
feat: add AI accounting recommendation workflow
test: add reconciliation edge cases
docs: add implementation roadmap
docs: add solutions demo script
```

Avoid:

```text
update
stuff
final
final2
changes
AI generated
```

---

# 39. DEFINITION OF DONE FOR EACH PHASE

A phase is complete only when:

1. Code / document exists.
2. It runs or can be reviewed.
3. It is tested where applicable.
4. README/documentation explains it.
5. Assumptions are documented.
6. Limitations are documented.
7. Git commit is made.
8. The candidate can explain it without the AI tool.

---

# 40. PORTFOLIO CASE STUDY

Create a concise case study.

Recommended structure:

## Problem

Northstar's close and reconciliation processes are manual and fragmented.

## Discovery

Summarise stakeholder findings.

## Current state

Show process map.

## Solution

Show target architecture.

## Build

Explain:

- SQL;
- Python;
- API;
- accounting automation;
- AI;
- controls.

## Results

Use measured POC metrics only.

For business targets that are assumptions, label them:

**Target**

not:

**Achieved**

## Lessons

Explain:

- technical lessons;
- accounting lessons;
- implementation lessons;
- AI-control lessons.

## Next steps

Explain what would be required for production.

---

# 41. TWO-PAGE EXECUTIVE CASE STUDY

The final PDF should ideally contain:

### Page 1

- project title;
- fictional client;
- problem;
- current state;
- target state;
- architecture;
- key metrics.

### Page 2

- solution;
- technical build;
- controls;
- implementation plan;
- lessons;
- portfolio / GitHub link.

---

# 46. WHAT NOT TO DO

Do NOT:

- build a generic chatbot;
- claim production ERP experience;
- invent real customer results;
- use real confidential data;
- blindly copy AI-generated code;
- build an overcomplicated microservices architecture;
- use AI everywhere;
- let AI post journals without controls;
- create a dashboard without solving the underlying workflow;
- focus only on code;
- omit accounting logic;
- omit implementation considerations;
- make the repository impossible for a reader to understand.

---

# 48. PROJECT PHASING / ESTIMATED EFFORT

Do not optimise for speed at the expense of understanding.

Suggested sequence:

### Week 1

- Discovery
- requirements
- current state
- future state
- architecture

### Week 2

- data model
- synthetic data
- SQL

### Week 3

- Python ingestion
- validation
- reconciliation

### Week 4

- REST API
- accounting automation
- tests

### Week 5

- AI workflow
- evaluation
- controls

### Week 6

- dashboard
- implementation plan
- migration plan

### Week 7

- demo
- case study
- executive PDF

### Week 8

- GitHub polish

This is flexible. The project can be completed faster or slower.

---

# 49. MILESTONE CHECKLIST

## Milestone 1 — Consulting foundation

- [ ] Client case defined
- [ ] Discovery script
- [ ] Stakeholder map
- [ ] Requirements
- [ ] Current-state process
- [ ] Future-state process

## Milestone 2 — Architecture

- [ ] Architecture diagram
- [ ] Data flows
- [ ] Integration map
- [ ] Security assumptions
- [ ] ADRs

## Milestone 3 — Data

- [ ] Schema
- [ ] Synthetic data
- [ ] Data-quality problems
- [ ] SQL queries

## Milestone 4 — Engineering

- [ ] Python ingestion
- [ ] Validation
- [ ] Reconciliation
- [ ] Tests

## Milestone 5 — Integration

- [ ] FastAPI
- [ ] CRUD endpoints
- [ ] Error handling
- [ ] API tests

## Milestone 6 — Accounting automation

- [ ] Rules
- [ ] Journal workflow
- [ ] Approval workflow
- [ ] Exception handling

## Milestone 7 — AI

- [ ] AI classification
- [ ] Confidence
- [ ] Evidence
- [ ] Human review
- [ ] Evaluation
- [ ] AI controls

## Milestone 8 — Productisation

- [ ] Dashboard
- [ ] Implementation plan
- [ ] Migration plan
- [ ] Demo

## Milestone 9 — Portfolio

- [ ] Case study
- [ ] Executive PDF
- [ ] GitHub README
- [ ] Demo video

---

# 50. ROOT README REQUIREMENTS

The root README must answer within the first screen:

1. What is this?
2. Who is it for?
3. What business problem does it solve?
4. What did I build?
5. What technologies were used?
6. What is fictional vs actually implemented?
7. How do I run it?
8. Where is the architecture?
9. Where is the demo?
10. What did I learn?

Suggested opening:

> **Northstar Finance OS** is an end-to-end finance transformation proof of concept for a fictional multi-entity healthcare group. It demonstrates how accounting process discovery can be translated into finance-system architecture, SQL data modelling, Python automation, REST API integration, reconciliation, AI-assisted accounting workflows and implementation planning.

---

# 51. AI CODING TOOL PROMPTING STANDARD

Whenever starting a new AI coding session, provide:

```text
You are contributing to the Northstar Finance OS portfolio project.

Read PLAN.md and AGENTS.md before making changes.

This is a fictional finance transformation / AI-native ERP proof of concept.

The project objective is to demonstrate:
- accounting domain understanding
- finance process discovery
- ERP/system architecture
- SQL
- Python ETL
- REST APIs
- reconciliation
- AI-assisted accounting
- accounting controls
- implementation planning
- solutions consulting

Do not invent production experience.
Do not use real financial or confidential data.
Do not add technologies merely for keywords.
Prefer simple, explainable architecture.
Do not make broad repository changes without first proposing a plan.

Before coding:
1. Inspect the relevant files.
2. Explain your proposed approach.
3. Identify assumptions.
4. Identify tests required.

After coding:
1. Run tests.
2. Explain what changed.
3. Explain any limitations.
4. Update documentation if architecture or behaviour changed.
```

Adapt this prompt to the specific AI coding tool.

---

# 52. HANDOFF PROTOCOL BETWEEN AI TOOLS

If switching from one AI coding tool to another:

1. Commit current work.
2. Update `PLAN.md`.
3. Update `AGENTS.md` if project-wide context changed.
4. Record incomplete work.
5. Record known bugs.
6. Record next task.
7. Give the next tool the repository.
8. Tell it to read `PLAN.md` and `AGENTS.md`.
9. Ask it to inspect current state before coding.

Never rely on the previous AI tool's conversational memory.

The repository is the source of truth.

---

# 53. PROJECT STATUS SECTION

At the top of `PLAN.md`, maintain:

```text
STATUS: Phase X — [name]
LAST UPDATED: YYYY-MM-DD

COMPLETED:
- ...

IN PROGRESS:
- ...

NEXT:
- ...

BLOCKERS:
- ...

KNOWN LIMITATIONS:
- ...

CURRENT TECH STACK:
- ...

LAST VERIFIED:
- Tests:
- API:
- Database:
- Dashboard:
```

Update this after every major milestone.

---

# 54. LEARNING METHOD

For every unfamiliar technical concept, use this loop:

1. Ask AI for a plain-English explanation.
2. Ask for a finance-specific example.
3. Implement it.
4. Break it intentionally.
5. Fix it.
6. Explain it back without AI.
7. Document it.

Examples:

- SQL joins
- API authentication
- idempotency
- database constraints
- ETL
- webhooks
- REST
- confidence thresholds
- AI evaluation

The objective is not merely to make the code run.

The objective is deep, explainable understanding.

---

# 56. FINAL PORTFOLIO PACKAGE

The final deliverable should contain:

1. GitHub repository
2. README
3. Architecture diagram
4. Current-state process map
5. Future-state process map
6. SQL schema and queries
7. Synthetic accounting dataset
8. Python ETL pipeline
9. Reconciliation engine
10. REST API
11. AI accounting workflow
12. AI evaluation
13. Controls documentation
14. Dashboard
15. Implementation plan
16. Migration plan
17. 10-minute demo
18. Two-page case study
19. Executive summary

---

# 57. THE SINGLE MOST IMPORTANT RULE

Do not optimise the project for “having lots of technology.”

Optimise it for this narrative:

**A finance expert identified a real accounting-process problem, discovered the root causes, designed a better operating model, translated it into system requirements, built a working technical proof of concept, applied AI selectively, designed appropriate controls, and can explain the solution to both a CFO and an engineer.**

That is the portfolio signal this project is intended to create.

---

# 58. FIRST TASK IN A NEW CONVERSATION

When starting a new AI conversation to work on this project, paste/upload this `PLAN.md` and the repository.

Use this opening message:

> I am building the Northstar Finance OS portfolio project described in PLAN.md. Treat PLAN.md as the canonical project specification. Read it fully before responding.
>
> I am using AI coding tools to build this incrementally. I want you to act as a combination of:
> - finance transformation consultant;
> - accounting systems expert;
> - solutions consultant coach;
> - senior software engineer;
> - AI product reviewer.
>
> Do not assume I have production ERP implementation, SQL, API integration or formal solutions consulting experience. The purpose of this project is to build practical evidence of those capabilities without misrepresenting my background.
>
> First, inspect the current repository and determine the current project phase from PLAN.md and the repository contents.
>
> Do not start coding immediately.
>
> First tell me:
> 1. what is already complete;
> 2. what is incomplete;
> 3. whether the repository is consistent with PLAN.md;
> 4. the next smallest meaningful milestone;
> 5. what you recommend I build next and why.
>
> When coding, make small incremental changes, explain important decisions, test everything, and update documentation.
>
> Challenge my accounting and systems reasoning rather than simply agreeing with me.

---

# 59. HOW THE USER SHOULD WORK WITH AI

The user should not outsource all thinking.

For major decisions, answer first and ask the AI to critique.

For example:

> “Here is how I would design the reconciliation workflow. Critique it as a senior finance-systems reviewer.”

Then:

> “Now turn the agreed design into implementation tasks.”

Then:

> “Implement task 1 only.”

Then:

> “Test it and explain what I need to understand about it.”

This creates a better project.

---

# 60. END STATE

When finished, the candidate should be able to walk a reviewer through:

**Customer discovery → accounting process → pain points → requirements → architecture → data model → SQL → Python → API → reconciliation → AI → controls → dashboard → implementation → demo → business value.**

That end-to-end chain is the core purpose of Northstar Finance OS.
