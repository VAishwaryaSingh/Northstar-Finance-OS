-- Reporting Queries — Northstar Finance OS (PLAN.md §20)
-- Run: psql -d northstar -f 05-sql/reporting.sql
--
-- All four queries read only from posted journal_entries/journal_lines --
-- the same finance data model the trial balance and close dashboard will
-- draw from later, per system-architecture.md's Outputs layer (R05).

-- 1. Revenue by entity
SELECT e.entity_code, coa.account_name, SUM(jl.credit_amount) AS revenue
FROM journal_lines jl
JOIN journal_entries je ON je.journal_entry_id = jl.journal_entry_id
JOIN entities e ON e.entity_id = je.entity_id
JOIN chart_of_accounts coa ON coa.account_id = jl.account_id
WHERE je.status = 'posted' AND coa.account_type = 'revenue'
GROUP BY e.entity_code, coa.account_name
ORDER BY e.entity_code, revenue DESC;

-- 2. Expenses by entity
SELECT e.entity_code, coa.account_name, SUM(jl.debit_amount) AS expense
FROM journal_lines jl
JOIN journal_entries je ON je.journal_entry_id = jl.journal_entry_id
JOIN entities e ON e.entity_id = je.entity_id
JOIN chart_of_accounts coa ON coa.account_id = jl.account_id
WHERE je.status = 'posted' AND coa.account_type = 'expense'
GROUP BY e.entity_code, coa.account_name
ORDER BY e.entity_code, expense DESC;

-- 3. Monthly movement -- net revenue and expense movement by entity/period
SELECT e.entity_code, je.period,
       SUM(CASE WHEN coa.account_type = 'revenue' THEN jl.credit_amount - jl.debit_amount ELSE 0 END) AS revenue_movement,
       SUM(CASE WHEN coa.account_type = 'expense' THEN jl.debit_amount - jl.credit_amount ELSE 0 END) AS expense_movement
FROM journal_lines jl
JOIN journal_entries je ON je.journal_entry_id = jl.journal_entry_id
JOIN entities e ON e.entity_id = je.entity_id
JOIN chart_of_accounts coa ON coa.account_id = jl.account_id
WHERE je.status = 'posted'
GROUP BY e.entity_code, je.period
ORDER BY e.entity_code, je.period;

-- 4. Currency exposure -- open (unpaid) AR/AP balances by currency, the
--    query behind the "same-day cash/FX position" the CFO asked for in
--    discovery-notes.md but couldn't get without asking Shared Services
SELECT i.currency, i.invoice_type, COUNT(*) AS invoice_count, SUM(i.amount) AS open_amount
FROM invoices i
LEFT JOIN payments p ON p.invoice_id = i.invoice_id
WHERE p.payment_id IS NULL
GROUP BY i.currency, i.invoice_type
ORDER BY i.currency, i.invoice_type;
