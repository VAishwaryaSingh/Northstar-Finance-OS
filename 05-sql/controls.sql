-- Controls Queries — Northstar Finance OS (PLAN.md §20)
-- Run: psql -d northstar -f 05-sql/controls.sql
--
-- These queries check for control gaps that schema.sql's constraints and
-- triggers don't (and shouldn't) rule out by construction -- e.g. nothing
-- stops a journal from being posted with no approver recorded; that has to
-- be *detected*, the same way current-state.md describes today's manual
-- approval evidence as "inconsistent."

-- 1. Journals posted without a recorded approval. schema.sql's
--    journal_entries_maker_checker_chk stops a journal approving itself,
--    but doesn't force every posted journal to have an approver at all --
--    this is the query that catches that gap (R06).
SELECT journal_entry_id, entity_id, period, status, created_by, approved_by
FROM journal_entries
WHERE status = 'posted' AND approved_by IS NULL;

-- 2. Journals above the approval threshold. Assumption, documented here
--    since no formal threshold exists yet: 10,000 in the entry's own
--    currency (GBP or USD), standing in for the "informal, unenforced"
--    threshold described in discovery-notes.md until Phase 11 formalises
--    one per PLAN.md §23.
WITH je_totals AS (
    SELECT je.journal_entry_id, e.entity_code, je.currency, je.status, je.approved_by,
           SUM(jl.debit_amount) AS total_amount
    FROM journal_entries je
    JOIN journal_lines jl ON jl.journal_entry_id = je.journal_entry_id
    JOIN entities e ON e.entity_id = je.entity_id
    GROUP BY je.journal_entry_id, e.entity_code, je.currency, je.status, je.approved_by
)
SELECT *,
       (approved_by IS NULL) AS missing_approval
FROM je_totals
WHERE total_amount > 10000
ORDER BY total_amount DESC;

-- 3. Transactions missing required metadata -- re-stages the raw source
--    CSVs just for this check, to show what a validation layer would catch
--    at the door, before a record is even eligible to enter the clean
--    schema (this is why these rows aren't in the `invoices` table at all --
--    see seed.sql's comments on excluded rows).
CREATE TEMP TABLE ctl_stg_invoices (
    invoice_id TEXT, invoice_type TEXT, invoice_number TEXT, entity_code TEXT, customer_code TEXT,
    vendor_code TEXT, vendor_name_raw TEXT, invoice_date TEXT, due_date TEXT, currency TEXT,
    amount TEXT, source TEXT, account_code TEXT, status TEXT, period TEXT
);
\copy ctl_stg_invoices FROM '04-data/invoices.csv' WITH (FORMAT csv, HEADER true)

-- Note: COPY ... CSV treats an empty, unquoted field as NULL (not '') by
-- default, so both blank and NULL are checked here.
SELECT invoice_id, invoice_type, invoice_number, 'missing entity_code' AS issue
FROM ctl_stg_invoices WHERE entity_code IS NULL OR entity_code = ''
UNION ALL
SELECT invoice_id, invoice_type, invoice_number, 'AP invoice with unmapped vendor (vendor_code blank)'
FROM ctl_stg_invoices WHERE invoice_type = 'AP' AND (vendor_code IS NULL OR vendor_code = '')
ORDER BY invoice_id;

DROP TABLE ctl_stg_invoices;
