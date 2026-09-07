-- AP Queries — Northstar Finance OS (PLAN.md §20)
-- Run: psql -d northstar -f 05-sql/ap.sql

-- 1. Unpaid invoices (AP invoices with no matching payment yet)
SELECT i.invoice_id, i.invoice_number, e.entity_code, v.vendor_name,
       i.invoice_date, i.due_date, i.currency, i.amount
FROM invoices i
JOIN entities e ON e.entity_id = i.entity_id
LEFT JOIN vendors v ON v.vendor_id = i.vendor_id
LEFT JOIN payments p ON p.invoice_id = i.invoice_id
WHERE i.invoice_type = 'AP' AND p.payment_id IS NULL
ORDER BY i.due_date;

-- 2. Overdue invoices (unpaid AP invoices past their due date, relative to
--    a fixed reference date standing in for "today" in this fictional dataset)
SELECT i.invoice_id, i.invoice_number, e.entity_code, v.vendor_name, i.due_date,
       (DATE '2026-09-07' - i.due_date) AS days_overdue, i.currency, i.amount
FROM invoices i
JOIN entities e ON e.entity_id = i.entity_id
LEFT JOIN vendors v ON v.vendor_id = i.vendor_id
LEFT JOIN payments p ON p.invoice_id = i.invoice_id
WHERE i.invoice_type = 'AP' AND p.payment_id IS NULL AND i.due_date < DATE '2026-09-07'
ORDER BY days_overdue DESC;

-- 3. Duplicate invoice candidates (same entity, same invoice number, same
--    type, appearing more than once) -- this is the SQL-side detection that
--    replaces the "caught only at payment run" pattern in current-state.md
--    (R10). Compare the row count here against 04-data/data-quality-log.md's
--    "Duplicate Invoice" section: it should surface all 6 planted pairs.
SELECT entity_id, invoice_number, invoice_type, COUNT(*) AS occurrences,
       ARRAY_AGG(invoice_id ORDER BY invoice_id) AS invoice_ids,
       ARRAY_AGG(amount ORDER BY invoice_id) AS amounts
FROM invoices
GROUP BY entity_id, invoice_number, invoice_type
HAVING COUNT(*) > 1
ORDER BY occurrences DESC;
