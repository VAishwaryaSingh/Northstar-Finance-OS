-- Northstar Finance OS — Seed Data Load
--
-- Loads the raw synthetic CSVs from 04-data/ (per PLAN.md §19, Phase 7) into
-- the schema created by schema.sql, resolving each source's natural business
-- keys (entity_code, customer_code, vendor_code, account_code) into the
-- schema's surrogate foreign keys (entity_id, customer_id, vendor_id,
-- account_id). This mapping step is a deliberately simple SQL version of
-- what the Phase 9 Python ingestion pipeline will do properly (with fuzzy
-- vendor-name matching, structured exception handling, etc.) -- here it's
-- plain joins, which is enough to prove the schema against real, messy data.
--
-- Rows whose natural key can't be resolved (blank entity_code, or an AP
-- invoice whose vendor_code was left unmapped because vendor_name_raw didn't
-- match the vendor master -- see 04-data/data-quality-log.md) are
-- deliberately EXCLUDED from the clean load and reported at the end. That's
-- not a bug: an unresolved record is exactly what should sit in an exception
-- queue rather than enter the finance data model, per R10/R11. Everything
-- else -- including duplicate invoices, duplicate payments, unmatched bank
-- and intercompany transactions, and incorrect account mappings -- loads
-- normally, because those are things the query sets in this folder (and,
-- later, the reconciliation engine) are supposed to find with SQL, not
-- things the load step should silently fix.
--
-- Run from the repo root (relative CSV paths below depend on it):
--   psql -d northstar -f 05-sql/seed.sql

BEGIN;

-- ===========================================================================
-- Staging tables: one per source CSV, columns as plain text, no constraints.
-- ===========================================================================

CREATE TEMP TABLE stg_entities (
    entity_id TEXT, entity_code TEXT, entity_name TEXT, country TEXT,
    functional_currency TEXT, status TEXT
);
CREATE TEMP TABLE stg_chart_of_accounts (
    account_code TEXT, account_name TEXT, account_type TEXT, normal_balance TEXT,
    account_id TEXT, status TEXT
);
CREATE TEMP TABLE stg_customers (
    customer_id TEXT, customer_code TEXT, customer_name TEXT, entity_code TEXT,
    billing_currency TEXT, status TEXT
);
CREATE TEMP TABLE stg_vendors (
    vendor_name TEXT, default_account_code TEXT, vendor_id TEXT, vendor_code TEXT, status TEXT
);
CREATE TEMP TABLE stg_fx_rates (
    fx_rate_id TEXT, currency_from TEXT, currency_to TEXT, rate_date TEXT, rate TEXT, source TEXT
);
CREATE TEMP TABLE stg_invoices (
    invoice_id TEXT, invoice_type TEXT, invoice_number TEXT, entity_code TEXT, customer_code TEXT,
    vendor_code TEXT, vendor_name_raw TEXT, invoice_date TEXT, due_date TEXT, currency TEXT,
    amount TEXT, source TEXT, account_code TEXT, status TEXT, period TEXT
);
CREATE TEMP TABLE stg_payments (
    payment_id TEXT, entity_code TEXT, invoice_id TEXT, payment_date TEXT, currency TEXT,
    amount TEXT, payment_type TEXT, source TEXT, status TEXT
);
CREATE TEMP TABLE stg_bank_transactions (
    bank_transaction_id TEXT, entity_code TEXT, bank_account_code TEXT, transaction_date TEXT,
    currency TEXT, amount TEXT, description TEXT, source TEXT, match_status TEXT, matched_payment_id TEXT
);
CREATE TEMP TABLE stg_journal_entries (
    journal_entry_id TEXT, entity_code TEXT, entry_date TEXT, period TEXT, currency TEXT,
    source TEXT, classification TEXT, status TEXT, created_by TEXT, approved_by TEXT, description TEXT
);
CREATE TEMP TABLE stg_journal_lines (
    journal_line_id TEXT, journal_entry_id TEXT, account_code TEXT,
    debit_amount TEXT, credit_amount TEXT, line_description TEXT
);
CREATE TEMP TABLE stg_intercompany_transactions (
    intercompany_transaction_id TEXT, entity_from_code TEXT, entity_to_code TEXT, transaction_date TEXT,
    currency TEXT, amount TEXT, reference TEXT, source TEXT, match_status TEXT, related_journal_entry_id TEXT
);

\copy stg_entities FROM '04-data/entities.csv' WITH (FORMAT csv, HEADER true)
\copy stg_chart_of_accounts FROM '04-data/chart_of_accounts.csv' WITH (FORMAT csv, HEADER true)
\copy stg_customers FROM '04-data/customers.csv' WITH (FORMAT csv, HEADER true)
\copy stg_vendors FROM '04-data/vendors.csv' WITH (FORMAT csv, HEADER true)
\copy stg_fx_rates FROM '04-data/fx_rates.csv' WITH (FORMAT csv, HEADER true)
\copy stg_invoices FROM '04-data/invoices.csv' WITH (FORMAT csv, HEADER true)
\copy stg_payments FROM '04-data/payments.csv' WITH (FORMAT csv, HEADER true)
\copy stg_bank_transactions FROM '04-data/bank_transactions.csv' WITH (FORMAT csv, HEADER true)
\copy stg_journal_entries FROM '04-data/journal_entries.csv' WITH (FORMAT csv, HEADER true)
\copy stg_journal_lines FROM '04-data/journal_lines.csv' WITH (FORMAT csv, HEADER true)
\copy stg_intercompany_transactions FROM '04-data/intercompany_transactions.csv' WITH (FORMAT csv, HEADER true)

-- ===========================================================================
-- Users -- not a source CSV (04-data/ has no users.csv; user accounts are
-- application/master data, not a source extract). Named to match the
-- created_by/approved_by initials generate_data.py used, and to the
-- Shared Services / Controller personas in discovery-notes.md.
-- ===========================================================================

INSERT INTO users (user_id, name, email, role) VALUES
    ('USR-001', 'G.Lin',     'g.lin@northstar-fake.example',     'preparer'),
    ('USR-002', 'T.Marsh',   't.marsh@northstar-fake.example',   'preparer'),
    ('USR-003', 'R.Adeyemi', 'r.adeyemi@northstar-fake.example', 'preparer'),
    ('USR-004', 'D.Okafor',  'd.okafor@northstar-fake.example',  'approver');

-- ===========================================================================
-- Reference / master data (no messiness injected upstream -- load directly)
-- ===========================================================================

INSERT INTO entities (entity_id, entity_code, entity_name, country, functional_currency, status)
SELECT entity_id, entity_code, entity_name, country, functional_currency, status FROM stg_entities;

INSERT INTO chart_of_accounts (account_id, account_code, account_name, account_type, normal_balance, status)
SELECT account_id, account_code, account_name, account_type, normal_balance, status FROM stg_chart_of_accounts;

INSERT INTO customers (customer_id, customer_code, customer_name, entity_id, billing_currency, status)
SELECT s.customer_id, s.customer_code, s.customer_name, e.entity_id, s.billing_currency, s.status
FROM stg_customers s JOIN entities e ON e.entity_code = s.entity_code;

INSERT INTO vendors (vendor_id, vendor_code, vendor_name, default_account_id, status)
SELECT s.vendor_id, s.vendor_code, s.vendor_name, a.account_id, s.status
FROM stg_vendors s LEFT JOIN chart_of_accounts a ON a.account_code = s.default_account_code;

INSERT INTO fx_rates (fx_rate_id, currency_from, currency_to, rate_date, rate, source)
SELECT fx_rate_id, currency_from, currency_to, rate_date::DATE, rate::NUMERIC, source FROM stg_fx_rates;

-- ===========================================================================
-- Invoices -- excludes rows with a blank entity_code (missing-entity-code
-- issue) or, for AP, a blank vendor_code (unmapped vendor-name issue).
-- Everything else, including the deliberately duplicated and mis-coded
-- rows, loads as-is.
-- ===========================================================================

INSERT INTO invoices (invoice_id, invoice_type, invoice_number, entity_id, customer_id, vendor_id,
                       invoice_date, due_date, currency, amount, source, account_id, status)
SELECT s.invoice_id, s.invoice_type, s.invoice_number, e.entity_id,
       c.customer_id, v.vendor_id,
       s.invoice_date::DATE, NULLIF(s.due_date, '')::DATE, s.currency, s.amount::NUMERIC,
       s.source, a.account_id, s.status
FROM stg_invoices s
JOIN entities e ON e.entity_code = s.entity_code
LEFT JOIN customers c ON c.customer_code = s.customer_code
LEFT JOIN vendors v ON v.vendor_code = s.vendor_code
LEFT JOIN chart_of_accounts a ON a.account_code = s.account_code
WHERE (s.invoice_type = 'AR' AND c.customer_id IS NOT NULL)
   OR (s.invoice_type = 'AP' AND v.vendor_id IS NOT NULL);

-- ===========================================================================
-- Payments -- entity always resolves (generated only from invoices that
-- already had a valid entity_code). invoice_id resolves to NULL if the
-- referenced invoice wasn't loaded above (e.g. it referenced an unmapped
-- vendor) -- the payment itself is still real and still loads.
-- ===========================================================================

INSERT INTO payments (payment_id, entity_id, invoice_id, payment_date, currency, amount,
                       payment_type, source, status)
SELECT s.payment_id, e.entity_id, i.invoice_id, s.payment_date::DATE, s.currency, s.amount::NUMERIC,
       s.payment_type, s.source, s.status
FROM stg_payments s
JOIN entities e ON e.entity_code = s.entity_code
LEFT JOIN invoices i ON i.invoice_id = NULLIF(s.invoice_id, '');

-- ===========================================================================
-- Bank transactions -- excludes the rows with a blank entity_code.
-- ===========================================================================

INSERT INTO bank_transactions (bank_transaction_id, entity_id, bank_account_code, transaction_date,
                                currency, amount, description, source, match_status, matched_payment_id)
SELECT s.bank_transaction_id, e.entity_id, s.bank_account_code, s.transaction_date::DATE,
       s.currency, s.amount::NUMERIC, s.description, s.source, s.match_status, p.payment_id
FROM stg_bank_transactions s
JOIN entities e ON e.entity_code = s.entity_code
LEFT JOIN payments p ON p.payment_id = NULLIF(s.matched_payment_id, '');

-- ===========================================================================
-- Journal entries + lines -- all resolve (no messiness was injected on
-- entity_code here). Loaded in one transaction with schema.sql's deferred
-- balance trigger, so the debit=credit check only runs once, at COMMIT.
-- ===========================================================================

INSERT INTO journal_entries (journal_entry_id, entity_id, entry_date, period, currency, source,
                              classification, status, created_by, approved_by, description)
SELECT s.journal_entry_id, e.entity_id, s.entry_date::DATE, s.period, s.currency, s.source,
       s.classification, s.status, u_created.user_id, u_approved.user_id, s.description
FROM stg_journal_entries s
JOIN entities e ON e.entity_code = s.entity_code
JOIN users u_created ON u_created.name = s.created_by
LEFT JOIN users u_approved ON u_approved.name = NULLIF(s.approved_by, '');

INSERT INTO journal_lines (journal_line_id, journal_entry_id, account_id, debit_amount,
                            credit_amount, line_description)
SELECT s.journal_line_id, s.journal_entry_id, a.account_id, s.debit_amount::NUMERIC,
       s.credit_amount::NUMERIC, s.line_description
FROM stg_journal_lines s
JOIN chart_of_accounts a ON a.account_code = s.account_code;

-- ===========================================================================
-- Intercompany transactions -- all resolve (no messiness injected on the
-- entity codes here; the messiness is the deliberately-missing counterpart
-- row on the unmatched side, already reflected in match_status).
-- ===========================================================================

INSERT INTO intercompany_transactions (intercompany_transaction_id, entity_from_id, entity_to_id,
                                        transaction_date, currency, amount, reference, source,
                                        match_status, related_journal_entry_id)
SELECT s.intercompany_transaction_id, ef.entity_id, et.entity_id, s.transaction_date::DATE,
       s.currency, s.amount::NUMERIC, s.reference, s.source, s.match_status,
       NULLIF(s.related_journal_entry_id, '')
FROM stg_intercompany_transactions s
JOIN entities ef ON ef.entity_code = s.entity_from_code
JOIN entities et ON et.entity_code = s.entity_to_code;

-- ===========================================================================
-- Approvals -- derived, not sourced from a CSV: one approval row per posted
-- journal entry (the maker/checker trigger in schema.sql already guarantees
-- approver_id <> created_by).
-- ===========================================================================

INSERT INTO approvals (approval_id, journal_entry_id, approver_id, decision, decision_date)
SELECT 'APR-' || je.journal_entry_id, je.journal_entry_id, je.approved_by, 'approved',
       je.entry_date::TIMESTAMP + INTERVAL '1 day'
FROM journal_entries je
WHERE je.status = 'posted' AND je.approved_by IS NOT NULL;

-- audit_logs is intentionally left empty here: it's populated by application
-- activity (Phase 9 ingestion, Phase 10 API), not by a synthetic source file.

COMMIT;

-- ===========================================================================
-- Load summary -- compare the "excluded" counts against
-- 04-data/data-quality-log.md's missing_entity_code (4) and
-- inconsistent_vendor_name (2) categories: they should match exactly.
-- ===========================================================================

SELECT 'entities' AS table_name, COUNT(*) AS rows_loaded FROM entities
UNION ALL SELECT 'users', COUNT(*) FROM users
UNION ALL SELECT 'chart_of_accounts', COUNT(*) FROM chart_of_accounts
UNION ALL SELECT 'customers', COUNT(*) FROM customers
UNION ALL SELECT 'vendors', COUNT(*) FROM vendors
UNION ALL SELECT 'fx_rates', COUNT(*) FROM fx_rates
UNION ALL SELECT 'invoices', COUNT(*) FROM invoices
UNION ALL SELECT 'payments', COUNT(*) FROM payments
UNION ALL SELECT 'bank_transactions', COUNT(*) FROM bank_transactions
UNION ALL SELECT 'journal_entries', COUNT(*) FROM journal_entries
UNION ALL SELECT 'journal_lines', COUNT(*) FROM journal_lines
UNION ALL SELECT 'intercompany_transactions', COUNT(*) FROM intercompany_transactions
UNION ALL SELECT 'approvals', COUNT(*) FROM approvals
ORDER BY table_name;

SELECT
    (SELECT COUNT(*) FROM stg_invoices) - (SELECT COUNT(*) FROM invoices) AS invoices_excluded;
