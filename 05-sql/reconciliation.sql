-- Bank Reconciliation Queries — Northstar Finance OS (PLAN.md §20)
-- Run: psql -d northstar -f 05-sql/reconciliation.sql

-- 1. Unmatched bank transactions (everything not cleanly matched to a payment)
SELECT b.bank_transaction_id, e.entity_code, b.transaction_date, b.currency,
       b.amount, b.description, b.match_status
FROM bank_transactions b
JOIN entities e ON e.entity_id = b.entity_id
WHERE b.match_status <> 'matched'
ORDER BY b.transaction_date;

-- 2. Matched transactions
SELECT b.bank_transaction_id, e.entity_code, b.transaction_date, b.currency,
       b.amount, b.matched_payment_id
FROM bank_transactions b
JOIN entities e ON e.entity_id = b.entity_id
WHERE b.match_status = 'matched'
ORDER BY b.transaction_date;

-- 3. Reconciliation rate, overall and by entity -- the automated replacement
--    for the "~80% manual" figure in discovery-notes.md (R02's success
--    metric is <=20% manual, i.e. this rate should sit at >=80% automated)
SELECT e.entity_code,
       COUNT(*) FILTER (WHERE b.match_status = 'matched') AS matched_count,
       COUNT(*) AS total_count,
       ROUND(100.0 * COUNT(*) FILTER (WHERE b.match_status = 'matched') / COUNT(*), 1) AS reconciliation_rate_pct
FROM bank_transactions b
JOIN entities e ON e.entity_id = b.entity_id
GROUP BY e.entity_code

UNION ALL

SELECT 'ALL ENTITIES',
       COUNT(*) FILTER (WHERE match_status = 'matched'),
       COUNT(*),
       ROUND(100.0 * COUNT(*) FILTER (WHERE match_status = 'matched') / COUNT(*), 1)
FROM bank_transactions
ORDER BY entity_code;
