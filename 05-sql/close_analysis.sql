-- Close Analysis Queries — Northstar Finance OS (PLAN.md §20)
-- Run: psql -d northstar -f 05-sql/close_analysis.sql

-- 1. Journals posted by day
SELECT je.entry_date, COUNT(*) AS journal_count
FROM journal_entries je
WHERE je.status = 'posted'
GROUP BY je.entry_date
ORDER BY je.entry_date;

-- 2. Manual vs. system-generated journals, by period, plus the overall split.
--    Sense-check this against discovery-notes.md's "~70% of journals are
--    manual" current-state figure -- this is the same measurement, now
--    queryable instead of estimated.
SELECT period, source, COUNT(*) AS journal_count
FROM journal_entries
GROUP BY period, source
ORDER BY period, source;

SELECT source, COUNT(*) AS journal_count,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_total
FROM journal_entries
GROUP BY source
ORDER BY source;

-- 3. Outstanding close tasks for the current close period -- anything not
--    yet posted is still open work, the automated equivalent of the
--    shared Excel close checklist in current-state.md (R01)
SELECT je.journal_entry_id, e.entity_code, je.period, je.classification,
       je.created_by, je.status
FROM journal_entries je
JOIN entities e ON e.entity_id = je.entity_id
WHERE je.period = '2026-08' AND je.status <> 'posted'
ORDER BY e.entity_code, je.journal_entry_id;
