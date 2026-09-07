-- Intercompany Queries — Northstar Finance OS (PLAN.md §20)
-- Run: psql -d northstar -f 05-sql/intercompany.sql

-- 1. Entity A vs Entity B -- transaction volume and value by direction
SELECT ef.entity_code AS entity_from, et.entity_code AS entity_to, ic.currency,
       COUNT(*) AS txn_count, SUM(ic.amount) AS total_amount
FROM intercompany_transactions ic
JOIN entities ef ON ef.entity_id = ic.entity_from_id
JOIN entities et ON et.entity_id = ic.entity_to_id
GROUP BY ef.entity_code, et.entity_code, ic.currency
ORDER BY ef.entity_code, et.entity_code;

-- 2. Amount differences between two sides sharing the same reference. In
--    this dataset matched pairs always agree exactly on amount (that's what
--    "matched" means here), so this should return zero rows -- it's included
--    because a real intercompany feed does see reference-matched pairs that
--    still disagree on amount (FX timing, partial settlement), and this is
--    the query that would catch it.
SELECT a.reference, a.entity_from_id AS side_a_entity, a.amount AS side_a_amount,
       b.entity_from_id AS side_b_entity, b.amount AS side_b_amount,
       (a.amount - b.amount) AS difference
FROM intercompany_transactions a
JOIN intercompany_transactions b
  ON a.reference = b.reference
 AND a.intercompany_transaction_id <> b.intercompany_transaction_id
WHERE a.amount <> b.amount;

-- 3. Missing counterpart entries -- the ~35/month exception pattern from
--    discovery-notes.md, now surfaced by a query instead of a shared
--    spreadsheet (R04). Compare against data-quality-log.md's
--    "Unmatched Intercompany Transaction" section.
SELECT ic.intercompany_transaction_id, ef.entity_code AS entity_from, et.entity_code AS entity_to,
       ic.transaction_date, ic.currency, ic.amount, ic.reference
FROM intercompany_transactions ic
JOIN entities ef ON ef.entity_id = ic.entity_from_id
JOIN entities et ON et.entity_id = ic.entity_to_id
WHERE ic.match_status = 'unmatched'
ORDER BY ic.transaction_date;
