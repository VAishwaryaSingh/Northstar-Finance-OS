# Python Data Pipeline — Northstar Finance OS

Implements the ingestion pipeline from PLAN.md §21:

```text
Source File -> Read -> Schema Validation -> Data Quality Checks ->
Duplicate Detection -> Entity/Account Mapping -> Currency Normalisation ->
Database Load -> Reconciliation -> Exception Report
```

This is the Python replacement for [05-sql/seed.sql](../05-sql/seed.sql)'s plain-SQL load of `invoices`, `payments`, `bank_transactions`, and `intercompany_transactions` — same four source-derived tables, but with real logic instead of a join: fuzzy vendor-name matching (recovers rows plain SQL had to drop), duplicate invoices flagged rather than silently loaded as normal, and bank/intercompany matches independently re-derived rather than trusted from the source data's own labels.

## Set up and run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest 06-python/tests -v      # unit tests, no database needed
.venv/bin/python 06-python/ingestion.py  # full pipeline, needs the northstar database (see 05-sql/README.md)
```

`ingestion.py` connects to the same local `northstar` PostgreSQL database Phase 8 set up (peer auth over the local unix socket, no password — see [db.py](./db.py)). It reads straight from `04-data/*.csv`, so run Phase 7/8 first if starting from scratch.

## Files

| File | Purpose |
|---|---|
| `db.py` | SQLAlchemy engine, reading `DATABASE_URL` from `.env` with a local-dev fallback |
| `mappings.py` | Resolves `entity_code`/`customer_code`/`vendor_code`/`account_code` to the schema's surrogate IDs; vendor resolution falls back to fuzzy name matching (`difflib`, no new dependency) when the code is unmapped |
| `validation.py` | Pydantic models — structural/type checks only (valid date, known currency, positive amount). A blank `entity_code` or an unresolvable vendor is *not* a validation failure here; those are data-quality/mapping concerns, kept in their own exception categories |
| `transformations.py` | Converts every amount into GBP using the nearest-dated rate in `fx_rates` (R08) |
| `reconciliation.py` | `flag_duplicate_invoices` (Python version of `ap.sql`'s duplicate detection, but it actually changes what loads); `match_transactions` and `match_intercompany` independently re-derive matches from amounts/dates/references instead of trusting the source's own `match_status` |
| `ingestion.py` | Orchestrates all of the above end to end, loads the result into PostgreSQL, and writes `exception-report.md` |
| `reconciliation_engine.py` | Phase 13 (PLAN.md §26) — the dedicated, deeper reconciliation engine: `reconcile_bank`, `reconcile_ap`, `reconcile_intercompany`, each with a four-tier `matched`/`probable_match`/`unmatched` output plus an exception reason. See "Phase 13" below |
| `run_reconciliation.py` | Runs the engine against the real database, writes `reconciliation-engine-results.md` |
| `tests/` | 40 pytest tests covering mapping, currency conversion, duplicate detection, ingestion-time reconciliation, and the Phase 13 engine |

## What actually improved over Phase 8's SQL-only load

| | `seed.sql` (Phase 8) | `ingestion.py` (Phase 9) |
|---|---|---|
| Invoices loaded | 86 / 92 | **88 / 92** — fuzzy vendor-name matching recovers the 2 AP invoices whose `vendor_name_raw` ("Med Supplies Ltd", "Medical Supplies Limited") didn't exactly match the vendor master |
| Duplicate invoices | found by a `GROUP BY` query, but still loaded as ordinary `open` invoices | flagged `duplicate_flagged` at load time — R10's actual requirement ("flagged before payment, not after"), not just detectable after the fact |
| Bank/intercompany matches | read straight from the source data's own `match_status` column | independently recomputed from amount/date/reference, so the result proves the matching logic works rather than that the label can be read back |
| Missing entity codes | rows silently excluded by an `INNER JOIN` | same exclusion, but logged with a reason in `exception-report.md` |

`exception-report.md` (regenerated on every run) is the ground truth to check this against: it should keep matching `04-data/data-quality-log.md`'s planted-issue counts, with two documented, expected differences (below).

## Two bugs this pipeline exposed, and how they were caught

Both were found by actually running the code against real data, not by review:

1. **`df.where(df.notna(), None)` didn't reliably turn a blank CSV cell into `None`** in this pandas version — it silently left some as `NaN`. Fixed in `validation.py` by cleaning each cell explicitly instead of relying on `.where()`.
2. **`NaN` is truthy in plain Python.** Building a DataFrame from a list of dicts turns a Python `None` into a float `NaN` whenever the same column also holds strings — and every `if not value:` / `if value is None:` blank-check in `mappings.py` and `ingestion.py` silently let `NaN` straight through instead of treating it as blank. `mappings.py` now has a `_blank()` helper that checks for `NaN` explicitly (with a regression test in `tests/test_mappings.py`); `ingestion.py`'s row-by-row exception logging was switched from `is None` to `pd.isna(...)`.

## A known, expected discrepancy (not a bug)

`04-data/data-quality-log.md` lists 6 planted duplicate-invoice pairs; `exception-report.md` only flags 5. The 6th pair is `INV-0004` / `INV-0091` — `INV-0004` also happens to be one of the 4 rows with a blank `entity_code`, so it's excluded from loading for that reason before duplicate detection ever runs, leaving `INV-0091` looking like an ordinary, non-duplicate invoice. This is two independent planted issues landing on the same underlying record, and it's the correct behaviour given that overlap (05-sql/ap.sql's SQL-only duplicate check finds the same 5, for the same reason) — not something to "fix" by loading unresolvable rows anyway.

## Known limitations

- The pipeline only covers the four tables that come from an external source (invoices, payments, bank_transactions, intercompany_transactions). `journal_entries`/`journal_lines` are produced by accounting automation (Phase 11) or manual entry, not ingested from a file, so they're out of scope here.
- Fuzzy vendor matching uses a fixed similarity cutoff (0.75) tuned against the two known name variants in the synthetic data — a larger vendor master with more genuinely similar-but-different names would need this threshold (and probably a smarter algorithm) revisited.
- `match_transactions`/`match_intercompany` (Phase 9, used by `ingestion.py`) use simple greedy nearest-match logic. `reconciliation_engine.py` (Phase 13, below) is the more careful version, with a probable-match tier and reasons — `ingestion.py` still uses the simpler Phase 9 versions since its job is deciding what loads, not producing a reconciliation report.

## Phase 13: Reconciliation Engine (PLAN.md §26)

```bash
.venv/bin/pytest 06-python/tests/test_reconciliation_engine.py -v
.venv/bin/python 06-python/run_reconciliation.py   # writes reconciliation-engine-results.md
```

Extends Phase 9's binary matched/unmatched with the four-tier output PLAN.md §26 asks for, across all three areas it names:

- **Bank** — matches on amount/date/counterparty (entity+currency), same as Phase 9 but with a `probable_match` tier for a close-but-not-exact candidate (a small amount variance or a wider date window), not just a hard yes/no.
- **AP** — matches invoices to payments on vendor's entity, amount, and a date window. Deliberately **ignores the schema's own `payments.invoice_id` foreign key** when searching for candidates, so this proves independent matching capability rather than reading a link back — and where its independent match disagrees with what that FK actually says, it flags the disagreement as its own finding.
- **Intercompany** — extends Phase 9's reference+amount matching with the two extra keys PLAN.md §26 asks for: the entity pair (both directions) and the period (the transaction's year-month), so a same-reference pair posted a few days either side of a period boundary comes back `probable_match`, not silently `matched`.

### What it found against the real database

| Area | Matched | Probable Match | Unmatched | Total |
|---|---|---|---|---|
| Bank | 68 | 0 | 10 | 78 |
| AP | 41 | 1 | 7 | 49 |
| Intercompany | 36 | 0 | 12 | 48 |

Bank and Intercompany's matched/unmatched counts land exactly on what Phase 9's simpler matching already found — a good consistency check between the two implementations, since Bank uses the same tight tolerances by default.

**AP's one `probable_match` is a genuinely interesting, traceable finding, not a synthetic example:** `INV-0059` independently matches to `PAY-0071`, but `PAY-0071`'s own `invoice_id` says it belongs to `INV-0086`. Tracing it back: `PAY-0062` and `PAY-0071` are the exact duplicate-payment pair Phase 7 deliberately planted for `INV-0086` (`04-data/data-quality-log.md`'s "Duplicate Payment" section). The engine correctly matches `INV-0086` to one of the two duplicates (`PAY-0062`) in its tight pass; the *other* duplicate (`PAY-0071`) is left over, unclaimed by any exact match, and the loose pass picks it up as the closest available (if imperfect) candidate for an unrelated invoice, `INV-0059` — which is exactly the kind of downstream confusion a real duplicate payment causes once it's in the system, not just the duplicate itself. This is a genuine consequence of the Phase 7 plant that no earlier phase's checks surfaced, because they all check *for* duplicates directly rather than for what a leftover duplicate payment does to unrelated reconciliation.
