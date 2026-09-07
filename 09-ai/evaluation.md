# AI Evaluation — Phase 12 (PLAN.md §31)

> "Do not say the AI works without evaluation."

## Method

`evaluate.py` runs 11 hand-built cases (`examples/*.json`) through the real `process_invoice` pipeline in `accounting_agent.py` — the same function any future posting workflow would call, not a simplified evaluation-only path. Each case pairs a canned model response (`MockLLMClient`) with a **ground truth** answer, spanning every category PLAN.md §30 asks for: high-confidence correct, low-confidence, ambiguous vendor, missing data, conflicting evidence, and adversarial/nonsensical input — plus three cases specific to this project's own rules (the approval threshold, an amount-outlier catch, and a deliberate "everything passes but it's still wrong" gap case).

Run it: `.venv/bin/python 09-ai/evaluate.py` (regenerates `evaluation-results.md`).

**Every number below describes `MockLLMClient`'s canned responses run through the safety pipeline — not a real model's classification accuracy.** See `llm_client.py`'s docstring and `controls.md`'s "Known limitations" for why no real model was run in this project.

## Results (from the last run — see `evaluation-results.md` for the full per-case table)

| Metric | Value |
|---|---|
| Classification accuracy | 64% (7/11) |
| Routed to human review | 73% (8/11) |
| False positives (flagged, but suggestion was fine) | 5/11 |
| False negatives (auto-approved, but suggestion was WRONG) | 1/11 |
| **Inappropriate automation rate** | **9% (1/11)** |

## Why accuracy is the least important number here

PLAN.md §31 is explicit: *"the most important metric is not simply model accuracy."* 64% accuracy sounds unimpressive next to a headline "the AI works" claim — and that's the point of measuring it this way instead. **Accuracy describes the model; the inappropriate automation rate describes the system.** A model that's right 95% of the time but wrong on the 5% it auto-approves without review is a worse system than one that's right 70% of the time but never auto-approves a wrong answer — because the first one is silently posting bad accounting entries. This evaluation is designed to make that distinction visible rather than let a single "% correct" figure hide it.

Read against that: this evaluation set's real headline is **every genuinely wrong suggestion with an observable red flag was caught** (EVAL-005, EVAL-006, EVAL-007, EVAL-011 — conflicting evidence, two hallucinations, and an amount outlier, all correctly flagged), and **every hallucination attempt was caught regardless of the confidence the model claimed** (EVAL-006, EVAL-007 — both stated 0.98+ confidence, both still flagged, because `validate_suggestion()` runs before confidence is even consulted).

## Two controls added after the first evaluation run found a gap

The first version of this evaluation (10 cases, no amount-outlier or audit-sampling checks) found a 10% inappropriate automation rate driven entirely by one deliberately-constructed case, `EVAL-010`. Rather than tune a rule to make that one case pass — which would be curve-fitting a test to itself, not a real improvement — two general-purpose controls were added to `08-accounting-automation` (see that module's `invoice_classification.check_amount_outlier` and `exception_rules.should_sample_for_audit`) and wired into `process_invoice`:

1. **Amount-outlier detection** — flags an invoice whose amount is a statistical outlier against that vendor's own history, even when the account matches and confidence is high. `EVAL-011` was added specifically to demonstrate this: everything about the suggestion is actually *correct*, but the amount (8,500) is wildly outside the vendor's normal 90–115 range, so it's still flagged. This catches a real, different, and probably more common failure mode than EVAL-010's.
2. **Random audit sampling** — a small, deterministic-per-ID fraction (5% by default) of every otherwise-clean, auto-approved transaction is flagged anyway, regardless of what else passed. This is the actual real-world answer to the category of risk no per-transaction rule can close.

## EVAL-010, honestly, after both new controls

`EVAL-010` is still in the evaluation set, unchanged in spirit: a vendor with a solid historical account match, a high-confidence correct-looking suggestion, an amount well within that vendor's *normal* range (110–125, deliberately not an outlier — this is the point), and no hallucinated codes. Ground truth says it's still wrong, because this was a genuine one-off exception nothing observable flags.

**In the run this file reflects, EVAL-010 was not selected by the audit sample and still comes back as a false negative.** That is not a scripted outcome — `evaluate.py` calls the real `should_sample_for_audit` function with no override, and this is what it actually returned this run. Because sampling is deterministic per invoice ID (not re-randomized on every run), re-running `evaluate.py` today will reproduce the exact same result; it would only start catching `EVAL-010` if the ID changed, the sample rate were raised, or a future signal specific to this case were added. That's the honest limit being reported, not a bug to quietly fix by re-rolling until it passes.

**What this demonstrates, taken together:** the amount-outlier check closed a real gap (proven by EVAL-011), and audit sampling adds a non-zero, statistically-guaranteed-over-time detection rate for the category neither that check nor any other can close deterministically — but it does not, and cannot, promise to catch any *specific* transaction. Over a large enough population, an average of 5% of the truly-invisible cases get caught by sampling alone; any individual one, including this one, might not be. **What this suggests for a real deployment** (a process/governance recommendation, not a further code change): either raise the sample rate for higher-risk vendor/amount combinations, or accept this residual rate as a documented, monitored risk rather than an assumed zero.

## Test-case coverage against PLAN.md §30

| §30 category | Case(s) |
|---|---|
| High-confidence correct | EVAL-001, EVAL-009 |
| Low-confidence | EVAL-002 |
| Ambiguous vendor | EVAL-003 |
| Missing data | EVAL-004 |
| Conflicting evidence | EVAL-005 |
| Adversarial / nonsensical input | EVAL-006, EVAL-007 |
| *(this project's own additions)* Approval threshold / amount outlier / inappropriate automation gap | EVAL-008 / EVAL-011 / EVAL-010 |
