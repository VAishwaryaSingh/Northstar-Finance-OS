# AI Evaluation — Phase 12 (PLAN.md §31)

> "Do not say the AI works without evaluation."

## Method

`evaluate.py` runs 10 hand-built cases (`examples/*.json`) through the real `process_invoice` pipeline in `accounting_agent.py` — the same function any future posting workflow would call, not a simplified evaluation-only path. Each case pairs a canned model response (`MockLLMClient`) with a **ground truth** answer, spanning every category PLAN.md §30 asks for: high-confidence correct, low-confidence, ambiguous vendor, missing data, conflicting evidence, and adversarial/nonsensical input — plus two cases specific to this project's own rules (the approval threshold, and a deliberate "everything passes but it's still wrong" gap case).

Run it: `.venv/bin/python 09-ai/evaluate.py` (regenerates `evaluation-results.md`).

**Every number below describes `MockLLMClient`'s canned responses run through the safety pipeline — not a real model's classification accuracy.** See `llm_client.py`'s docstring and `controls.md`'s "Known limitations" for why no real model was run in this project.

## Results (from the last run — see `evaluation-results.md` for the full per-case table)

| Metric | Value |
|---|---|
| Classification accuracy | 60% (6/10) |
| Routed to human review | 70% (7/10) |
| False positives (flagged, but suggestion was fine) | 4/10 |
| False negatives (auto-approved, but suggestion was WRONG) | 1/10 |
| **Inappropriate automation rate** | **10% (1/10)** |

## Why accuracy is the least important number here

PLAN.md §31 is explicit: *"the most important metric is not simply model accuracy."* 60% accuracy sounds unimpressive next to a headline "the AI works" claim — and that's the point of measuring it this way instead. **Accuracy describes the model; the inappropriate automation rate describes the system.** A model that's right 95% of the time but wrong on the 5% it auto-approves without review is a worse system than one that's right 70% of the time but never auto-approves a wrong answer — because the first one is silently posting bad accounting entries. This evaluation is designed to make that distinction visible rather than let a single "% correct" figure hide it.

Read against that: this evaluation set's real headline is **90% of wrong suggestions here were correctly caught before automation** (3 of 4 incorrect cases were flagged: EVAL-005, EVAL-006, EVAL-007), and **every hallucination attempt was caught regardless of the confidence the model claimed** (EVAL-006, EVAL-007 — both stated 0.98+ confidence, both still flagged, because `validate_suggestion()` runs before confidence is even consulted).

## The one case that didn't get caught: EVAL-010

`EVAL-010` (`inappropriate_automation_gap`) is deliberately constructed, not a bug: a vendor with a solid, well-matched historical default, a high-confidence model suggestion that agrees with that default, an amount under the approval threshold, no hallucinated codes — every single check this system has passes. And the ground truth says it's still wrong, because this particular invoice was a genuine one-off exception nothing available to the system flagged as unusual.

This is the honest limit of a rules + confidence + hallucination-check safety net: it catches wrong answers that *look* wrong by some signal (low confidence, a code that doesn't exist, a mismatch with a known default). It cannot catch a wrong answer that looks exactly like a right one. No evaluation methodology makes that risk zero — the value of measuring `inappropriate_automation_rate` explicitly is knowing the number isn't zero, rather than assuming it is because every documented control passed.

**What this suggests for a real deployment** (not implemented here, since it's a process/governance recommendation, not a code change): periodic human sampling of a small percentage of *auto-approved* transactions too, not just the ones already flagged — the only way to catch this category of error at all, since by construction nothing in the automated pipeline can distinguish it from a correct case.

## Test-case coverage against PLAN.md §30

| §30 category | Case(s) |
|---|---|
| High-confidence correct | EVAL-001, EVAL-009 |
| Low-confidence | EVAL-002 |
| Ambiguous vendor | EVAL-003 |
| Missing data | EVAL-004 |
| Conflicting evidence | EVAL-005 |
| Adversarial / nonsensical input | EVAL-006, EVAL-007 |
| *(this project's own addition)* Approval threshold | EVAL-008 |
| *(this project's own addition)* Inappropriate automation gap | EVAL-010 |
