# SQL — Northstar Finance OS

Implements the schema from [data-model.md](../03-architecture/data-model.md) as PostgreSQL DDL, loads it with the synthetic data from [04-data/](../04-data/), and answers the query categories PLAN.md §20 asks for: AP, bank reconciliation, intercompany, close analysis, reporting, and controls.

**Everything in this folder has actually been run against a real PostgreSQL 15 database, not just reviewed by eye** — including deliberately trying to insert a self-approved journal and an unbalanced journal, to prove the constraints reject them.

## Set up a local database

If you don't already have PostgreSQL, on a Debian/Ubuntu-based Linux environment (including a Chromebook's Linux/Crostini container):

```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib
sudo service postgresql start
sudo -u postgres psql -c "CREATE ROLE <your-username> WITH LOGIN CREATEDB;"
sudo -u postgres psql -c "CREATE DATABASE northstar OWNER <your-username>;"
```

Replace `<your-username>` with your own Linux username — this creates a database role that owns the `northstar` database, rather than doing everything as the `postgres` superuser (same least-privilege principle as [security-model.md](../03-architecture/security-model.md)).

## Run it, in order, from the repo root

```bash
psql -d northstar -f 05-sql/schema.sql   # creates all 14 tables, constraints, triggers
psql -d northstar -f 05-sql/seed.sql     # loads 04-data/*.csv into the schema
psql -d northstar -f 05-sql/ap.sql
psql -d northstar -f 05-sql/reconciliation.sql
psql -d northstar -f 05-sql/intercompany.sql
psql -d northstar -f 05-sql/close_analysis.sql
psql -d northstar -f 05-sql/reporting.sql
psql -d northstar -f 05-sql/controls.sql
```

Run from the repo root specifically — `seed.sql` and `controls.sql` load CSVs using paths relative to wherever `psql` is started (`04-data/...`).

## Files

| File | Purpose |
|---|---|
| `schema.sql` | All 14 tables from data-model.md, plus two enforced accounting rules (below) |
| `seed.sql` | Loads `04-data/*.csv`, resolving natural business keys (`entity_code`, `customer_code`, etc.) into the schema's surrogate foreign keys |
| `ap.sql` | Unpaid invoices, overdue invoices, duplicate invoice candidates |
| `reconciliation.sql` | Unmatched/matched bank transactions, reconciliation rate by entity |
| `intercompany.sql` | Entity-pair volumes, amount differences, missing counterpart entries |
| `close_analysis.sql` | Journals posted by day, manual vs. system split, outstanding close tasks |
| `reporting.sql` | Revenue/expense by entity, monthly movement, currency exposure |
| `controls.sql` | Journals posted without approval, journals above threshold, transactions missing required metadata |

PLAN.md §20 groups these into `reconciliation.sql`, `close_analysis.sql`, `intercompany.sql`, `reporting.sql`; `ap.sql` and `controls.sql` are added beyond that list so each of the six query categories in §20 gets its own file rather than being folded into an unrelated one.

## The two accounting rules enforced by the database itself

These aren't just documented in data-model.md — `schema.sql` makes the database itself reject bad data:

1. **Debit = credit.** A `journal_entries` row can have its `journal_lines` built up freely while `status = 'draft'`. The moment it's not in draft (posted, approved, pending_approval...), a deferred trigger checks that its lines' debits and credits sum to the same total, and raises an error at commit if they don't.
2. **Maker ≠ checker.** A `CHECK` constraint stops `journal_entries.approved_by` ever equalling `journal_entries.created_by`, and a trigger enforces the same rule on the `approvals` table.

Both were tested by deliberately trying to break them (see the commit history / conversation — a self-approved journal and an unbalanced journal were both rejected by PostgreSQL, and a correctly-formed one committed successfully) before this was considered done.

## Why some rows don't load

`seed.sql` deliberately **excludes** 6 of the 92 source invoices (and the 3 bank transactions with a blank entity code) from the clean schema — the ones where `entity_code` is blank or an AP invoice's vendor couldn't be matched to the vendor master (see [04-data/data-quality-log.md](../04-data/data-quality-log.md)). That's not a bug: those records can't satisfy the schema's `NOT NULL entity_id` / `NOT NULL vendor_id` requirements, and in a real system they'd sit in an exception queue rather than enter the finance data model silently. `controls.sql`'s third query re-stages the raw CSV specifically to show what got caught at the door.

Everything else messy — duplicate invoices, duplicate payments, unmatched bank/intercompany transactions, incorrect account mappings — **does** load, because those are exactly what `ap.sql`, `reconciliation.sql`, and `intercompany.sql` are meant to detect with SQL, not something the load step should quietly fix.

## Known limitations

- No automated test suite for these queries yet (SQL doesn't have an equivalent of pytest built into PLAN.md's toolchain) — correctness here was verified by manual execution and eyeballing results against `data-quality-log.md`'s known counts. Phase 9's Python pipeline will have real pytest coverage.
- The approval threshold used in `controls.sql` (10,000) is a documented assumption, not a real Northstar Health Group policy — there isn't one yet; Phase 11 formalises this properly.
- `seed.sql`'s code→id mapping is plain SQL joins, not the fuzzy vendor-name matching or structured exception handling the real ingestion pipeline (Phase 9) will have.
