# Known Issues, Bugs & Limitations — Northstar Finance OS

Every phase's own `README.md`/`controls.md` documents its own limitations where they arise (that's deliberate — see AGENTS.md's Definition of Done, which requires it per phase). This file exists because a reviewer shouldn't have to open eleven different files to get the full picture. Nothing below is new; every item links back to its original, fuller discussion. Consistent with this project's own stated principle throughout: disclose real gaps plainly, don't bury or minimise them.

## 1. Real bugs found and fixed during development

Found by actually running code against real data, not by code review alone. Bugs 2 and 3 have dedicated regression tests so they can't silently come back; bug 1 has only related tests, and bug 4 has none.

| # | Bug | Root cause | Impact | Fix |
|---|---|---|---|---|
| 1 | Blank CSV cells weren't reliably becoming `None` | `df.where(df.notna(), None)` doesn't behave consistently across pandas versions/dtypes | Would have let malformed rows through validation silently | Clean each cell explicitly instead of relying on `.where()` — [06-python/validation.py](./06-python/validation.py) |
| 2 | Blank/`None` values silently passed "is this blank?" checks | Building a DataFrame from a list of dicts turns Python `None` into a float `NaN` whenever the column also holds strings — and `NaN` is truthy in plain Python, so `if not value:` and `if value is None:` both miss it | Every blank-code check in the ingestion pipeline was silently broken until this was found | Added an explicit `_blank()` helper checking for `NaN`; switched `is None` checks to `pd.isna(...)` — [06-python/mappings.py](./06-python/mappings.py), [06-python/ingestion.py](./06-python/ingestion.py), regression test in `06-python/tests/test_mappings.py` |
| 3 | Dashboard's data-quality metric returned 281 findings when the real number was 17 | A SQL query was missing 3 of the 5 columns (`invoice_date`, `currency`, `amount`) the rule actually checks — every invoice looked like it was "missing" fields it actually had | 264 false positives out of 281 total findings, on every single one of the 88 real invoices | Added the missing columns to the query; permanent regression test `test_data_quality_exceptions_has_no_false_missing_field_hits` — [10-dashboard/README.md](./10-dashboard/README.md) |
| 4 | A deprecated Streamlit call (`use_container_width`) in the dashboard | Found while verifying the dashboard with Streamlit's headless `AppTest` | Minor — a deprecation warning, not wrong output | Replaced the call. Previously recorded only in the dashboard commit message |

## 2. A known, deliberate discrepancy (not a bug)

`04-data/data-quality-log.md` plants 6 duplicate-invoice pairs; every downstream detection (SQL, Python pipeline, accounting-automation rules, reconciliation engine) only ever finds 5. The 6th pair's original invoice (`INV-0004`) is *also* one of the 4 rows with a blank `entity_code`, so it gets excluded from the loaded data for that reason before duplicate detection ever runs — leaving its duplicate (`INV-0091`) looking like an ordinary invoice with nothing to compare against. Two independent planted issues landing on the same record. The same overlap hides one of the 5 planted incorrect-account-mapping issues (`INV-0029`, also a blank-`entity_code` row), so the rules catch 4 of 5. Confirmed correct, consistent behaviour across every phase that touches it — not something to "fix" by loading unresolvable rows. Full detail: [06-python/README.md](./06-python/README.md).

## 3. The AI safety evaluation's disclosed gap

The most important item on this page. [09-ai/evaluation.md](./09-ai/evaluation.md) deliberately constructed a test case (`EVAL-010`) where every documented AI safety control passes — high confidence, matches the vendor's usual account, a normal amount, real codes — and the ground truth is still wrong, because nothing observable flags it as unusual. It was reported as a genuine ~9-10% "inappropriate automation rate," not hidden or minimised.

When asked whether this could be fixed, the honest answer is: not completely, by any per-transaction rule — that's a property of any rule-based or ML-based detection system, not an implementation shortfall. Two real, general controls were added in response (an amount-outlier check, and random audit sampling of even "clean" transactions), and **`EVAL-010` was re-tested afterward and still was not caught** on that run (not selected by the 5% random sample) — reported as-is, not re-run until it looked better. Full discussion, including why this is the correct way to report it: [09-ai/evaluation.md](./09-ai/evaluation.md), [09-ai/controls.md](./09-ai/controls.md).

**Related, smaller finding:** the new amount-outlier check, run against the real database, flagged 7 of 49 real AP invoices (~14%) — genuinely higher than a real deployment should see. That's not the rule being noisy; it's this project's synthetic data generator drawing invoice amounts independently and uniformly at random per invoice rather than clustering them around a realistic per-vendor typical amount, combined with small per-vendor sample sizes (3-6 invoices) inflating the statistical spread. Explained in full, including the one obvious, real 40-standard-deviation outlier the rule correctly caught: [08-accounting-automation/controls.md](./08-accounting-automation/controls.md).

## 4. Documented assumptions (not yet confirmed with a real client)

None of these are hidden defaults — each is a named constant with a comment explaining it's a placeholder, not a researched figure:

| Assumption | Value | Where | Would need |
|---|---|---|---|
| Journal approval threshold | £/$10,000 | [08-accounting-automation/journal_workflow.py](./08-accounting-automation/journal_workflow.py) | Confirmation with the Controller before go-live ([discovery-notes.md](./01-discovery/discovery-notes.md) confirms today's threshold is informal and unenforced — there's no real figure to have used instead) |
| Random audit sample rate | 5% | [08-accounting-automation/exception_rules.py](./08-accounting-automation/exception_rules.py) | Setting per actual risk appetite, likely higher for higher-value vendor relationships |
| Amount-outlier tolerance | 3 standard deviations | [08-accounting-automation/invoice_classification.py](./08-accounting-automation/invoice_classification.py) | Re-tuning against real (not synthetic) vendor invoice history |
| Fuzzy vendor-name match cutoff | 0.75 similarity | [06-python/mappings.py](./06-python/mappings.py) | Re-tuning against a real vendor master with more name variants than this dataset's two known examples |
| AI confidence threshold | 0.95 | [09-ai/accounting_agent.py](./09-ai/accounting_agent.py) | PLAN.md's own example policy value — not independently validated against real model output, since no real model call has been made (see §5) |

## 5. Integration gaps — built and tested independently, not yet wired together

Each phase was deliberately kept reviewable on its own rather than everything being connected end-to-end in one pass:

- **No real LLM call has been made anywhere in this project.** [09-ai/llm_client.py](./09-ai/llm_client.py)'s `AnthropicLLMClient` is real, correct, working code — untested without an `ANTHROPIC_API_KEY`, by the user's explicit choice. Every AI evaluation number describes the safety pipeline given `MockLLMClient`'s canned responses, not a real model's judgement.
- **08-accounting-automation's and 09-ai's rules aren't called from the live API.** `07-api/schemas.py` validates balance and maker≠checker; it doesn't call `determine_journal_status`, `classify_vendor_account`, or the AI assistant when a request actually comes in.
- **09-ai's audit trail isn't persisted.** `OverrideRecord` has the right shape to become a row in `schema.sql`'s `audit_logs` table; `accounting_agent.py` doesn't actually write to Postgres.
- **`accounting_agent.py` doesn't pull vendor history automatically.** The amount-outlier check's `vendor_historical_amounts` parameter has to be supplied by the caller — it's not queried from the database inside the AI pipeline itself, even though the underlying check has been proven against real data via `08-accounting-automation/run_rules.py`.
- **07-api doesn't use 06-python's fuzzy vendor matching.** `POST /invoices`/`POST /payments` expect a `vendor_code` that already exists — an API caller is expected to send a real code, the way a real integration partner would, not free text needing to be resolved.

## 6. Scope boundaries — by design, documented, not oversights

- **Authentication is a single shared API key**, not per-user identity or roles ([07-api](./07-api/)) — matches [security-model.md](./03-architecture/security-model.md)'s explicitly stated POC scope: no real identity provider, MFA, session management, penetration testing, or encryption-at-rest configuration.
- **No pagination** on `GET` endpoints — fine at this dataset's size, would need addressing before scaling.
- **No dashboard caching/auto-refresh or dashboard-level authentication** ([10-dashboard/](./10-dashboard/)) — every page load re-runs every query live; anyone reaching the Streamlit process can view it.
- **No automated test suite for the raw SQL query files** in [05-sql/](./05-sql/) — correctness was verified by manual execution against known counts; Phase 9's Python layer has full pytest coverage instead.
- **No rendered architecture diagrams** — `current-state.png`/`future-state.png`/`system-architecture.png` were never drawn; ASCII flow diagrams stand in throughout.
- **No demo video** — this session's environment has no screen-recording capability. [11-demo/demo-script.md](./11-demo/demo-script.md) and `demo-flow.md` are written to be directly usable as the source for recording one.

## 7. Planted issues with no dedicated detector

The synthetic data plants 9 categories of problem ([04-data/data-quality-log.md](./04-data/data-quality-log.md)). Six are caught (with the two explained misses above). Three are not detected by any check in this repo — they load into the database without a flag:

| Planted issue | Count | Status |
|---|---|---|
| Duplicate payments | 4 pairs | No detector. The only trace is indirect: the AP reconciliation's one `probable_match` (`INV-0059` ↔ `PAY-0071`) is a side-effect of the `INV-0086` duplicate pair ([06-python/README.md](./06-python/README.md)) |
| Late-posted journals (`JE-0031`, `JE-0036`) | 2 | No period cut-off check |
| Unapplied cash (`PAY-0072`–`PAY-0076`, no `invoice_id`) | 5 | The API allows a missing `invoice_id` by design; there is no exception category or ageing report for it |

Natural next controls: a duplicate-payment rule, a period cut-off rule, and an unapplied-cash report. Full planted-vs-caught table: [evidence/bugs-and-detection.md](./evidence/bugs-and-detection.md).

## Full risk register

[12-implementation/risks.md](./12-implementation/risks.md) covers 10 risks a real deployment would need to actively manage, each tied to a specific mitigation already built or explicitly planned — several of the items above (the approval threshold, the audit-sample rate, the AI evaluation gap) appear there too, framed as deployment risk rather than a development-time finding.
