# AI Safety / Control Requirements — Phase 12 (PLAN.md §25)

> **The AI must never silently post accounting entries without controls.**

Every requirement PLAN.md §25 lists, and exactly where it's implemented:

| Requirement | Implementation |
|---|---|
| Confidence threshold | `CONFIDENCE_THRESHOLD = 0.95` in `accounting_agent.py`, checked in `process_invoice` — matches PLAN.md §25's own example policy |
| Human review | `AIRecommendation.requires_human_review` — the final field every caller checks; nothing downstream of `process_invoice` is meant to act on a recommendation without checking this first |
| Approval threshold | Reused from Phase 11, not reimplemented — `journal_workflow.approval_requirement` (see "Why this calls into Phase 11" below) |
| Audit log | `OverrideRecord` in `accounting_agent.py`, structurally matching `schema.sql`'s `audit_logs` table (performed_by, reason, what was overridden) — see Known limitations for what's not yet wired up |
| Source evidence | `AIRecommendation.reasoning`, carried straight through from the model's own stated reasoning — never fabricated by this layer |
| Deterministic validation | `classify_vendor_account` from `08-accounting-automation/invoice_classification.py`, called directly (not reimplemented) inside `process_invoice` |
| Exception queue | Every invoice with `requires_human_review = True` and a populated `review_reasons` list *is* the exception queue entry — see Known limitations for where this would actually live in a real system |
| Segregation of duties | Not this module's job — enforced upstream by `schema.sql`'s maker≠checker constraint and `07-api`'s validation; an AI recommendation is never itself an approval |
| Ability to override AI recommendation | `override_recommendation()` |
| Reason for override | Same function — raises `ValueError` on a blank or whitespace-only reason. Not advisory: there is no code path to record an override without one |
| No hallucinated accounting data | `validate_suggestion()` — checked *first*, before confidence or anything else, and confidence cannot override it (see `test_adversarial_hallucinated_account_forces_review_even_at_high_confidence`) |

## The policy actually implemented

PLAN.md §25's example policy, implemented exactly (not just documented) in `process_invoice`:

```text
Confidence >= 0.95
AND all deterministic validation checks pass (Phase 11's rules, not a copy of them)
AND no hallucinated account/entity code
AND transaction below the approval threshold (Phase 11's rule, not a new number)
→ eligible for automated workflow (requires_human_review = False)

Otherwise → human review
```

## Why this calls into Phase 11 instead of reimplementing it

`08-accounting-automation/exception_rules.py` deliberately reimplements small pieces of `06-python/reconciliation.py` rather than cross-importing (see that module's own `controls.md` for why). This module does the opposite — it imports `08-accounting-automation` directly (`sys.path` trick, same as every other cross-phase script here). The difference: Phase 9 vs. Phase 11 were two *reasonable, independent* implementations of a similar idea at different points in a pipeline. Phase 12's AI safety boundary is not that kind of case — the whole point of "rules handle deterministic controls, AI only assists" is that the AI is checked by the *one* real rule engine, not a second opinion that could quietly drift out of sync with it. A safety boundary that could disagree with itself isn't a safety boundary.

## Two controls added after evaluation found a gap

The first evaluation run (see `evaluation.md`) found a genuine inappropriate-automation case (`EVAL-010`): a transaction where every check above passes, and the outcome is still wrong. Two general-purpose controls were added in response, both reused from `08-accounting-automation` the same way as everything else in this table — not new one-off logic living only in this module:

| Addition | Implementation | What it actually closes |
|---|---|---|
| Amount-outlier detection | `invoice_classification.check_amount_outlier`, called as step 5 in `process_invoice` | A vendor's invoice amount being far outside their own historical range, even when the account and confidence look fine — proven by `evaluation.md`'s `EVAL-011` |
| Random audit sampling | `exception_rules.should_sample_for_audit`, called as step 6 | The category neither this nor any other per-transaction rule can close deterministically: a genuine anomaly that matches nothing else on file. Adds a non-zero, statistically-guaranteed-over-time detection rate (5% by default) for exactly that category — not a promise to catch any specific transaction |

`evaluation.md`'s "EVAL-010, honestly, after both new controls" section reports what actually happened when these were run against the original gap case — including that it still wasn't caught that run, and why that's the correct, non-cherry-picked outcome to report rather than a failure to fix.

## Known limitations

- **No real model has been run.** Every number in `evaluation-results.md` comes from `MockLLMClient` — a deterministic stand-in, not a real model's judgement. `AnthropicLLMClient` in `llm_client.py` is a real, correct implementation (Claude Haiku 4.5, strict tool use) that would work with an `ANTHROPIC_API_KEY` set, but it was not exercised in this project, by the user's own choice (offline-first for this phase — see the session this was built in). Re-running `evaluate.py` with `AnthropicLLMClient` swapped in for `MockLLMClient` would produce real model numbers using the exact same pipeline and metrics.
- **The audit log isn't wired into the database yet.** `OverrideRecord` has the right shape to become a row in `schema.sql`'s `audit_logs` table, but `accounting_agent.py` doesn't write to Postgres — that integration (alongside wiring these rules into `07-api`, itself already a noted Phase 11 limitation) is a natural next step, not done here to keep this phase reviewable on its own.
- **The exception queue is conceptual, not a real table/UI.** A `requires_human_review = True` recommendation needs somewhere a human actually goes to review it — that's Phase 14's Close Control Centre dashboard's job, not this phase's.
- **`should_sample_for_audit`'s 5% rate is a documented assumption**, the same category as the 10,000 approval threshold — not a validated policy figure. A real deployment would set this per risk appetite, possibly higher for higher-value vendor relationships.
- **The amount-outlier check itself has been run against real data** — see `08-accounting-automation/controls.md`, which found 7 real outliers among 49 real AP invoices via `run_rules.py`. What hasn't been built is `accounting_agent.py` pulling a given invoice's vendor history from the database automatically — `process_invoice`'s `vendor_historical_amounts` parameter has to be supplied by the caller (the evaluation cases supply it directly). Same "not wired into a live workflow yet" limitation as the rest of this list, just for this one parameter specifically.
- **EVAL-010 in `evaluation-results.md` remains a known, honest gap, not a bug.** Even with both controls above, it demonstrates that every documented control passing is still not a formal guarantee of correctness — see `evaluation.md`'s full discussion.
