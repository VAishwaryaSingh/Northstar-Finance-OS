# Data Model — Northstar Finance OS

Detailed design of the **Finance Data Model** component from [system-architecture.md](./system-architecture.md)'s Core layer — the single entity-aware relational model that replaces the fragmented per-entity spreadsheets and inconsistent chart of accounts described in [current-state.md](../02-process-mapping/current-state.md) (R07, R09). This is a logical design (entities, fields, relationships, constraints) — the physical implementation as PostgreSQL DDL (`05-sql/schema.sql`, per [ADR-0001](../ADRs/0001-postgresql-as-primary-database.md)) follows in Phase 8, and will implement exactly what's specified here.

Minimum table set per PLAN.md §18: `entities`, `customers`, `vendors`, `chart_of_accounts`, `invoices`, `payments`, `bank_transactions`, `journal_entries`, `journal_lines`, `intercompany_transactions`, `fx_rates`, `users`, `approvals`, `audit_logs`.

## Two accounting principles enforced at the model level

These are non-negotiable per PLAN.md §18 and are enforced by the schema itself, not left to application logic to remember:

1. **Debit = Credit.** Every `journal_entries` header must have its child `journal_lines` sum to zero net (`SUM(debit_amount) − SUM(credit_amount) = 0`). This is enforced as a database constraint in Phase 8 (a `CHECK` at the application/service layer plus a reconciling trigger, or an equivalent constraint the PostgreSQL implementation chooses) — a journal entry is never in a persisted, non-draft state where debits and credits disagree.
2. **Every transaction carries entity, date, currency, source, accounting classification, and status.** `invoices`, `payments`, `bank_transactions`, `journal_entries`, and `intercompany_transactions` all carry these six fields directly (named per-table below), so nothing enters the model without knowing which entity it belongs to, what it is, and where it stands in its lifecycle.

## Entity-relationship overview

```text
                         ┌───────────┐
                         │  entities │
                         └─────┬─────┘
             ┌───────┬─────────┼─────────┬────────────────┐
             ▼        ▼        ▼         ▼                ▼
       ┌──────────┐┌────────┐┌────────┐┌────────────┐┌─────────────────────┐
       │customers ││vendors ││invoices││journal_     ││intercompany_         │
       │          ││        ││        ││entries      ││transactions          │
       └────┬─────┘└───┬────┘└───┬────┘└──────┬──────┘└──────────┬──────────┘
            │          │         │            │                  │
            │          │         ▼            ▼                  │ (entity_from/entity_to,
            │          │   ┌───────────┐┌─────────────┐           │  both → entities)
            │          │   │ payments  ││journal_lines│           │
            │          │   └─────┬─────┘└──────┬──────┘           │
            │          │         │              │ account_id       │
            │          │         ▼              ▼                 │
            │          │   ┌──────────────┐┌──────────────────┐   │
            └──────────┴──▶│bank_         ││chart_of_accounts │   │
                       │    │transactions  │└──────────────────┘   │
                       │    └──────────────┘                       │
                       │                                           │
        ┌──────────┐   │         ┌───────────┐   ┌─────────────┐  │
        │fx_rates  │   │         │  users    │──▶│  approvals  │◀─┘ (journal_entry_id)
        └──────────┘   │         └─────┬─────┘   └─────────────┘
                        │               │ created_by / approved_by
                        │               ▼
                        │         ┌──────────────┐
                        └────────▶│ audit_logs   │◀── every table above writes here
                                  └──────────────┘
```

## Table-by-table data dictionary

### `entities`
The legal entities in the group (per discovery: two UK entities, one US entity — GBP and USD functional currencies).

| Field | Type | Description / constraint |
|---|---|---|
| entity_id | PK | |
| entity_code | text, unique | e.g. `NHG-UK1`, `NHG-US` |
| entity_name | text | |
| country | text | |
| functional_currency | text (currency code) | e.g. `GBP`, `USD` |
| status | enum: active, inactive | |

### `users`
Ties directly to the role-based access model in [security-model.md](./security-model.md) — enforces R12.

| Field | Type | Description / constraint |
|---|---|---|
| user_id | PK | |
| name | text | |
| email | text, unique | |
| role | enum: preparer, approver, viewer, ingestion_service, admin | drives maker/checker enforcement below |
| status | enum: active, inactive | |

### `chart_of_accounts`
One CoA shared across all entities (R07 — fixes today's per-entity CoA drift).

| Field | Type | Description / constraint |
|---|---|---|
| account_id | PK | |
| account_code | text, unique | |
| account_name | text | |
| account_type | enum: asset, liability, equity, revenue, expense | |
| normal_balance | enum: debit, credit | used to validate journal_lines direction |
| status | enum: active, inactive | |

### `customers`
Single master source (R09) — a customer exists once, referenced by whichever entity bills them.

| Field | Type | Description / constraint |
|---|---|---|
| customer_id | PK | |
| customer_code | text, unique | |
| customer_name | text | |
| entity_id | FK → entities | owning/billing entity |
| billing_currency | text (currency code) | |
| status | enum: active, inactive | |

### `vendors`
Single master source (R09); `default_account_id` is the deterministic vendor→account mapping rule from [ADR-0003](../ADRs/0003-deterministic-rules-before-ai.md) — resolved by a rule first, AI only if unmapped.

| Field | Type | Description / constraint |
|---|---|---|
| vendor_id | PK | |
| vendor_code | text, unique | |
| vendor_name | text | raw source data is inconsistent (e.g. "Med Supplies Ltd" vs "Medical Supplies Limited") — normalisation happens at ingestion, not here; this field holds the resolved/canonical name |
| default_account_id | FK → chart_of_accounts, nullable | |
| status | enum: active, inactive | |

### `invoices`
Covers both AR (billing platform → customer invoices) and AP (vendor invoices) with a type discriminator, since both flow through the same duplicate-detection and mapping logic (R10) and differ only in which master-data side they reference.

| Field | Type | Description / constraint |
|---|---|---|
| invoice_id | PK | |
| invoice_type | enum: AR, AP | |
| invoice_number | text | not globally unique — source data reuses invoice numbers across entities, so uniqueness is enforced on `(entity_id, invoice_number, invoice_type)`, not on the number alone |
| entity_id | FK → entities | mandatory transaction field |
| customer_id | FK → customers, nullable | required when invoice_type = AR |
| vendor_id | FK → vendors, nullable | required when invoice_type = AP |
| invoice_date | date | mandatory transaction field |
| due_date | date | |
| currency | text (currency code) | mandatory transaction field |
| amount | decimal(18,2) | |
| source | text | mandatory transaction field — e.g. `billing_api`, `ap_csv` |
| classification | text/FK → chart_of_accounts, nullable until resolved | mandatory transaction field — resolved by deterministic rule or AI suggestion |
| status | enum: open, paid, void, duplicate_flagged | mandatory transaction field |

### `payments`

| Field | Type | Description / constraint |
|---|---|---|
| payment_id | PK | |
| entity_id | FK → entities | mandatory transaction field |
| invoice_id | FK → invoices, nullable | nullable to allow unapplied cash |
| payment_date | date | mandatory transaction field |
| currency | text (currency code) | mandatory transaction field |
| amount | decimal(18,2) | |
| payment_type | enum: received, made | |
| source | text | mandatory transaction field |
| status | enum: pending, matched, unmatched | mandatory transaction field |

### `bank_transactions`
Feeds the Reconciliation Engine ([system-architecture.md](./system-architecture.md)); `match_status` drives the reconciliation exception queue (R02).

| Field | Type | Description / constraint |
|---|---|---|
| bank_transaction_id | PK | |
| entity_id | FK → entities | mandatory transaction field |
| bank_account_code | text | |
| transaction_date | date | mandatory transaction field |
| currency | text (currency code) | mandatory transaction field |
| amount | decimal(18,2) | |
| description | text | raw bank memo/reference — the field reconciliation matching logic parses |
| source | text | mandatory transaction field, e.g. `bank_csv` |
| match_status | enum: unmatched, probable_match, matched, exception | mandatory transaction field |
| matched_payment_id | FK → payments, nullable | |

### `journal_entries` (header)

| Field | Type | Description / constraint |
|---|---|---|
| journal_entry_id | PK | |
| entity_id | FK → entities | mandatory transaction field |
| entry_date | date | mandatory transaction field |
| period | text (e.g. `2026-09`) | close period this entry belongs to |
| currency | text (currency code) | mandatory transaction field |
| source | enum: system, manual, ai_assisted | mandatory transaction field |
| classification | text | mandatory transaction field — e.g. accrual, intercompany, FX revaluation |
| status | enum: draft, pending_approval, approved, posted, rejected | mandatory transaction field |
| created_by | FK → users | |
| approved_by | FK → users, nullable | **must differ from created_by** — enforced constraint, this is R12's maker/checker rule at the model level |
| description | text | |

### `journal_lines`

| Field | Type | Description / constraint |
|---|---|---|
| journal_line_id | PK | |
| journal_entry_id | FK → journal_entries | |
| account_id | FK → chart_of_accounts | |
| debit_amount | decimal(18,2), default 0 | |
| credit_amount | decimal(18,2), default 0 | exactly one of debit/credit is non-zero per line |
| line_description | text | |

**Constraint enforced across every `journal_entries` header:** `SUM(journal_lines.debit_amount) = SUM(journal_lines.credit_amount)` for all lines sharing that `journal_entry_id`, before the header can move out of `draft` status.

### `intercompany_transactions`
Automated matching by entity/reference/amount/currency/period (R04) replaces the shared-spreadsheet process in [current-state.md](../02-process-mapping/current-state.md).

| Field | Type | Description / constraint |
|---|---|---|
| intercompany_transaction_id | PK | |
| entity_from_id | FK → entities | |
| entity_to_id | FK → entities | |
| transaction_date | date | mandatory transaction field |
| currency | text (currency code) | mandatory transaction field |
| amount | decimal(18,2) | |
| reference | text | matching key, along with entity/amount/currency/period |
| source | text | mandatory transaction field |
| match_status | enum: unmatched, matched, exception | mandatory transaction field |
| related_journal_entry_id | FK → journal_entries, nullable | populated once posted |

### `fx_rates`
Defined, auditable rate source (R08) — replaces today's ad hoc month-end spot rate entered in Excel.

| Field | Type | Description / constraint |
|---|---|---|
| fx_rate_id | PK | |
| currency_from | text (currency code) | |
| currency_to | text (currency code) | |
| rate_date | date | |
| rate | decimal(18,8) | |
| source | text | the named, documented rate provider — auditability requirement from R08 |

### `approvals`
The system of record for sign-off that today only exists as email/paper ([discovery-notes.md](../01-discovery/discovery-notes.md)) — satisfies R06.

| Field | Type | Description / constraint |
|---|---|---|
| approval_id | PK | |
| journal_entry_id | FK → journal_entries | |
| approver_id | FK → users | must differ from `journal_entries.created_by` |
| decision | enum: approved, rejected | |
| decision_date | timestamp | |
| comments | text, nullable | |

### `audit_logs`
Immutable log satisfying R11 — every table above writes here on insert/update/status change, never the reverse.

| Field | Type | Description / constraint |
|---|---|---|
| audit_log_id | PK | |
| table_name | text | which table changed |
| record_id | text | PK of the affected row |
| action | enum: insert, update, approve, reject, override | |
| performed_by | FK → users | |
| performed_at | timestamp | |
| before_value | text/JSON, nullable | |
| after_value | text/JSON, nullable | |
| reason | text, nullable | **required (not nullable) when action = override** — this is where an AI-suggested treatment override is logged with justification, per the AI safety policy (PLAN.md §25) |

## Requirement coverage check

| Requirement | Satisfied by |
|---|---|
| R02 (automated reconciliation) | `bank_transactions.match_status`, `payments`, reconciliation logic against both |
| R04 (intercompany matching) | `intercompany_transactions` |
| R06 (approval audit trail) | `journal_entries.approved_by` + `created_by` ≠ constraint, `approvals` |
| R07 (single CoA across entities) | `chart_of_accounts` referenced by every entity, no per-entity duplication |
| R08 (FX policy) | `fx_rates` with mandatory `source` |
| R09 (single master data source) | `customers`, `vendors` as shared master tables, not per-entity copies |
| R10 (duplicate invoice detection) | `invoices.status = duplicate_flagged`, uniqueness constraint on `(entity_id, invoice_number, invoice_type)` |
| R11 (immutable audit trail) | `audit_logs`, written by every other table |
| R12 (maker/checker) | `journal_entries.created_by ≠ approved_by` constraint, `approvals`, `users.role` |

R01, R03, R05 are process/integration outcomes rather than single tables — they depend on this model existing and being populated by the ingestion pipeline (Phase 9) and API (Phase 10), not on a dedicated table of their own.

## What's next

Phase 7 (`04-data/generate_data.py`) generates synthetic CSVs against this exact structure, deliberately including the messiness described in PLAN.md §19 (duplicate invoices, missing entity codes, unmatched bank/intercompany transactions). Phase 8 (`05-sql/schema.sql`) turns every table above into PostgreSQL DDL, including the debit=credit and maker≠checker constraints as enforced database constraints, not just documented rules.
