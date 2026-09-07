# Controls — Accounting Automation (Phase 11, PLAN.md §23)

## The critical distinction this phase exists to protect

> **Rules should handle deterministic accounting controls. AI should assist with ambiguous classification / explanation / exception handling.**

Phase 12 (the AI assistant) is built next, and every one of its recommendations will pass through the rules in this folder before it can touch anything — the rules aren't advisory context for the AI to weigh, they're a hard boundary it operates inside. This phase has to exist, and be solid, before that one starts.

## What's implemented, and what each rule replaces

| Rule (PLAN.md §23 example) | Module | Replaces / formalises |
|---|---|---|
| Invoice vendor → default account mapping | `invoice_classification.classify_vendor_account` | Was invisible until now — Phase 7 deliberately planted 5 "incorrect account mapping" invoices specifically for this rule to catch (see below); nothing before this phase checked it |
| Entity → ledger mapping | `invoice_classification.validate_entity_ledger` | Trivial with one shared chart of accounts, but checked explicitly rather than assumed |
| Currency → FX requirement | `invoice_classification.requires_fx_conversion` | Flags the need; `06-python/transformations.py` already does the actual conversion math |
| Invoice amount → approval threshold | `journal_workflow.approval_requirement`, `determine_journal_status` | Formalises the placeholder assumption `05-sql/controls.sql` could only leave as a comment (10,000, still not a real Northstar policy — see Known assumptions) |
| Duplicate invoice → exception | `exception_rules.check_duplicate_invoices` | Same idea as `06-python/reconciliation.py`'s duplicate flagging, reimplemented here as a standing policy check rather than an ingestion-time fix (see "Why this isn't just imported from 06-python" below) |
| Missing tax field → exception | `exception_rules.check_required_fields` | This data model doesn't track a separate tax field (see `data-model.md`) — generalised to the fields `data-model.md` actually declares mandatory on every transaction |
| Intercompany transaction → counterpart validation | `exception_rules.check_intercompany_counterpart` | Same idea as `06-python/reconciliation.py`'s intercompany matching, reimplemented as a standing check |
| *(added post-Phase 12)* Amount → vendor-history outlier | `invoice_classification.check_amount_outlier` | Not a PLAN.md §23 example — added after Phase 12's evaluation (`09-ai/evaluation.md`) found a case where every rule above passes but the result is still wrong. Flags an invoice amount that's a statistical outlier against that vendor's own history |
| *(added post-Phase 12)* Random audit sampling | `exception_rules.should_sample_for_audit` | Also added after that same finding — the honest answer to the residual category no per-transaction rule can close: a small, deterministic fraction of even fully-clean transactions gets flagged anyway |

## Proven against real data, not just unit tests

`run_rules.py` runs every rule above against the actual `northstar` database and writes `rule-findings.md`. Compare its counts to what earlier phases already know about this dataset:

- **5 duplicate invoices** — matches Phase 8/9 exactly (the 6th planted duplicate's counterpart was already excluded at load time for an unrelated reason — missing entity code — so it was never in the table to compare against; see `06-python/README.md`'s "known, expected discrepancy" for the identical situation)
- **4 incorrect account mappings** — Phase 7 planted 5; the 5th (`INV-0029`) was also one of the rows excluded at load time for a missing entity code, same overlap as above. This rule is the first thing in the whole project to actually check for this issue — it was invisible through Phases 7–10.
- **12 unmatched intercompany transactions** — matches Phase 8/9 exactly
- **19 intercompany transactions requiring FX conversion** — a real result, not a planted one: with one USD entity and two GBP entities, any intercompany transaction touching the USD entity crosses a currency boundary. (Invoices never do, in this dataset — every invoice is billed in its own entity's own functional currency by construction, so `requires_fx_conversion` has nothing to catch there; see `run_rules.py`'s comment.)
- **0 journal entries posted without the approval their amount required** — expected, not a gap: the synthetic data generator always attaches an approver whenever it marks an entry `posted`, regardless of amount, so there was nothing for this check to catch in this dataset. The rule itself is still meaningful — it protects against a future entry point (a script, a manual DB edit) that skips the amount-aware check `07-api`'s client-side validation and `schema.sql`'s constraints don't cover.
- **7 amount outliers, out of 49 AP invoices (~14%)** — added post-Phase 12 (see below), using leave-one-out per vendor (each invoice's "history" is every other AP invoice from the same vendor). That 14% is genuinely higher than a real deployment should expect, and it's honest to say why: this dataset's synthetic AP amounts are drawn independently and uniformly at random per invoice (`04-data/generate_data.py`), not clustered around a realistic per-vendor typical amount the way real invoices are, and most vendors here only have 3-6 invoices total — both push the leave-one-out standard deviation artificially low. The rule is doing exactly what it's supposed to (see `INV-0058`: 40.2 standard deviations, a real, obvious outlier by any measure); this dataset just isn't realistic enough to demonstrate a low false-positive rate for it. A production deployment would want more invoices per vendor before trusting this check's precision.

## Why this isn't just imported from 06-python

`06-python/reconciliation.py` already has duplicate-invoice and intercompany-matching logic. This phase reimplements small, focused versions instead of importing across directories, for two reasons: neither `06-python` nor `08-accounting-automation` is a valid Python package name (both start with a digit), so a cross-import needs the same `sys.path` hack twice over; and conceptually they're answering slightly different questions — Phase 9's version cleans a messy source file on the way in, this phase's version is a standing accounting policy that could just as well run against already-loaded data (e.g. a resubmission through the API). Keeping each phase's deliverable self-contained and independently reviewable was judged more valuable here than removing ~40 lines of duplication.

## Known assumptions and limitations

- **The 10,000 approval threshold is still not a real Northstar Health Group policy.** `discovery-notes.md` is explicit that today's threshold is informal and unenforced. This module is where that assumption now lives (superseding the placeholder note in `05-sql/controls.sql`) — a real engagement would confirm the actual figure with the Controller before this went anywhere near production.
- **These rules aren't wired into `07-api` yet.** `07-api/schemas.py` validates balance and maker≠checker; it doesn't yet call `journal_workflow.determine_journal_status` or `invoice_classification.classify_vendor_account` when a request comes in. Wiring them in is a natural next integration step, deliberately not done in this phase to keep it reviewable on its own.
- **`check_required_fields` found nothing in this dataset**, and that's expected: every invoice that made it into the `invoices` table already passed entity/customer/vendor resolution back in Phase 8/9 — anything missing a required field was already excluded before it got this far. The rule exists for defence in depth (e.g. a future code path that loads data differently), not because this dataset currently needs it.
- **`should_sample_for_audit` hasn't been run against the real database.** It's unit-tested (including a 20,000-ID convergence test) and proven in `09-ai/evaluation.md`, but wasn't added to `run_rules.py` — sampling doesn't produce "findings" in the same sense as the other rules (it's a proactive selection, not an anomaly detection), so mixing it into the same report would muddy what `rule-findings.md` is actually showing. `check_amount_outlier`, by contrast, *has* been run against real data — see above.
