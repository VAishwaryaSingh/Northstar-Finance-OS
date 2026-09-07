# Migration Plan — Northstar Finance OS

PLAN.md §29's four sections, grounded in what [discovery-notes.md](../01-discovery/discovery-notes.md) actually says would need to move, and in the concrete detection/mapping capability already built and proven in this repository — this isn't a generic migration checklist, it's this project's own tooling pointed at the question "what happens when this is real legacy data, not synthetic."

## Data inventory

What moves from the legacy per-entity ERP, per [discovery-notes.md](../01-discovery/discovery-notes.md)'s Technology section:

| Data | Volume (approx.) | Notes |
|---|---|---|
| Chart of accounts | 3 entity-specific CoAs → 1 shared CoA | Today's CoAs differ slightly by entity ([current-state.md](../02-process-mapping/current-state.md)) — this is exactly what [ADR](../ADRs/)-driven single-CoA design fixes, not a migration afterthought |
| Customer master | Per-entity informal lists | No single source of truth today (R09) |
| Vendor master | Per-entity informal lists, inconsistent naming | The exact problem [06-python/mappings.py](../06-python/mappings.py)'s fuzzy matching already solves for source-file ingestion — see Mapping, below |
| Open AP/AR balances | At cutover date | Migrated as opening balances (Implementation Plan Phase 6) |
| Transaction history | At least 12 months (discovery-notes.md, for trend reporting) | Migrated as read-only history, not re-posted through the new controls (see Cleansing) |
| Intercompany balances | Per the shared spreadsheet ([current-state.md](../02-process-mapping/current-state.md)) | A live reconciliation exercise before cutover, not a straight data copy — unresolved differences need resolving before they migrate, not after |

## Mapping

**Legacy account → target account.** A real crosswalk file (legacy code → `chart_of_accounts.account_code`), reviewed by the Controller — this project's synthetic dataset skips straight to the target CoA since there's no real legacy system to map from, but [data-model.md](../03-architecture/data-model.md)'s single shared CoA is exactly what the crosswalk would map *into*.

**Legacy entity → target entity.** Trivial here (3 legacy entities → the same 3 target entities, per [ADR-0004](../ADRs/0004-retain-legacy-erp-initially.md)'s decision to retain rather than restructure) — a real multi-entity consolidation might collapse or split entities, which this migration would need to handle explicitly, not assume away.

**Legacy vendor → target vendor.** The one mapping category this project has already built and proven real tooling for: [06-python/mappings.py](../06-python/mappings.py)'s `map_vendor` resolves an exact `vendor_code` where available, and falls back to fuzzy name matching (`difflib`, cutoff 0.75) where the legacy name doesn't exactly match — proven in Phase 9 to recover 2 real AP invoices a plain SQL join couldn't (see [06-python/README.md](../06-python/README.md)). A real vendor-master migration runs this same logic (or a stronger version of it, given more real name variants than this synthetic dataset's two) against the legacy vendor list, not a manual spreadsheet reconciliation.

## Cleansing

The exact four categories PLAN.md §29 names, each with the detection logic already built in this repository rather than described only in the abstract:

| Cleansing category | Detection already built | Where |
|---|---|---|
| Duplicates | `check_duplicate_invoices` — exact-key duplicate detection (entity, invoice number, invoice type) | [08-accounting-automation/exception_rules.py](../08-accounting-automation/exception_rules.py) |
| Invalid codes | `classify_vendor_account`, `validate_entity_ledger` — any code that doesn't resolve to something real | [08-accounting-automation/invoice_classification.py](../08-accounting-automation/invoice_classification.py) |
| Missing fields | `check_required_fields` — entity, date, currency, amount, status, and AR/AP-specific customer/vendor presence | [08-accounting-automation/exception_rules.py](../08-accounting-automation/exception_rules.py) |
| Inactive suppliers | `vendors.status = 'inactive'` — not actively used by any rule yet in this POC, but the schema already carries the field; a real migration would exclude inactive vendors from the target master rather than migrate dead records | [05-sql/schema.sql](../05-sql/schema.sql) |

Every one of these is already proven to work against real (if synthetic) messy data — see [04-data/data-quality-log.md](../04-data/data-quality-log.md) for the ground truth these rules were built and tested against, and [08-accounting-automation/rule-findings.md](../08-accounting-automation/rule-findings.md) / [06-python/exception-report.md](../06-python/exception-report.md) for the actual findings.

## Validation

PLAN.md §29's five validation categories, each with the real query/tool already built:

| Validation | Tool | Where |
|---|---|---|
| Record counts | Row counts before/after migration, per table | [05-sql/seed.sql](../05-sql/seed.sql)'s load summary pattern |
| Balances | Opening balance = legacy closing balance, per entity/account | [07-api](../07-api/)'s `GET /trial-balance`, or [05-sql/reporting.sql](../05-sql/reporting.sql) directly |
| Control totals | Sum of migrated transaction amounts = legacy system's own control total | Same trial balance / reporting queries, cross-checked against a legacy extract total kept for exactly this purpose |
| Trial balance | Debits = credits, post-migration, at the account level | Guaranteed by construction — [schema.sql](../05-sql/schema.sql)'s deferred trigger won't let an unbalanced journal exist in the first place, so a post-migration trial balance imbalance would mean a migration script bug, not an accounting error slipping through |
| Reconciliation | Migrated bank/AP/intercompany balances reconcile the same way live data does | [06-python/reconciliation_engine.py](../06-python/reconciliation_engine.py) run against the migrated data, same as any other period |

**Cutover principle:** migrated historical transactions load as already-posted, read-only history — they do not re-run through [08-accounting-automation](../08-accounting-automation/)'s live rules or [09-ai](../09-ai/)'s AI assistant. Those controls govern new transactions from go-live forward; retroactively re-classifying 12 months of legacy history against rules that didn't exist when those transactions were originally posted would create findings with no one left to action them, not a real control improvement.
