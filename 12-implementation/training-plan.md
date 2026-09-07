# Training Plan — Northstar Finance OS

Tied to the [Rollout Plan](./rollout-plan.md)'s schedule — each entity's users are trained before that entity's cutover, not all at once at the start of the programme.

## Who, and on what

| Audience | What's changing for them | Training focus |
|---|---|---|
| Shared Services team (preparers) | Manual re-keying → automated ingestion; manual reconciliation → [reconciliation engine](../06-python/reconciliation_engine.py) output; exceptions now land in a queue instead of being discovered at month-end | How to read an exception (missing entity code, duplicate flagged, amount outlier), when to fix the source data vs. escalate, how [journal_workflow.py](../08-accounting-automation/journal_workflow.py)'s approval routing changes their day-to-day (they can no longer post-and-forget above the threshold) |
| Entity Controllers (approvers) | Email/paper sign-off → system-enforced maker≠checker approval; ad hoc review → structured [Close Control Centre](../10-dashboard/) view | How to interpret an AI recommendation's confidence and reasoning ([09-ai/prompts.md](../09-ai/prompts.md)'s output shape) before approving or overriding it — and that overriding always requires a reason ([override_recommendation](../09-ai/accounting_agent.py)), not a silent click-through |
| Group Financial Controller | Manual reporting assembly (~2 days, [current-state.md](../02-process-mapping/current-state.md)) → live [trial balance](../07-api/README.md)/reporting endpoints | How close progress, manual journal %, and outstanding reconciliation metrics on the dashboard map to what they used to track by hand in Excel |
| CFO | Asking Shared Services to manually check cash/IC position → same-day dashboard view | Reading the [Close Control Centre](../10-dashboard/) directly — this audience needs the dashboard, not the underlying tooling |
| IT/systems owner (for a real deployment; not part of this POC's fictional personas) | New system to operate and monitor | Deployment, `.env`/secrets management ([.env.example](../.env.example)), what "known limitations" in each phase's `controls.md`/`README.md` mean operationally |

## Format

- **Hands-on workshops**, not slide decks — each session runs through a real exception end to end (a duplicate invoice, an amount outlier, an AI recommendation awaiting review) using that entity's own pilot/rollout data, not a generic demo dataset
- **Quick-reference guides** per role, one page each, built from the relevant `controls.md`/`README.md` already written for every phase in this repository — training material is a curated view onto documentation that already exists, not written from scratch
- **A dedicated support channel during each entity's first close cycle** (see [rollout-plan.md](./rollout-plan.md)'s parallel-run period) — this is when questions actually surface, not during the workshop itself

## Timing

Training for an entity's preparers and approvers completes **before** that entity's cutover date, per the [Rollout Plan](./rollout-plan.md) schedule:

| Stage | Training window | Audience |
|---|---|---|
| Pilot | 1-2 weeks before Shared Services Ltd cutover | Shared Services team, that entity's Controller |
| Rollout 1 | 1 week before Holdings Ltd cutover | That entity's preparers/Controller (Shared Services team already trained) |
| Rollout 2 | 2 weeks before Health Services Inc cutover (longer lead time — first entity exercising FX logic live, per [risks.md](./risks.md) R10) | That entity's preparers/Controller |
| Ongoing | At go-live and continuously | CFO (dashboard), Group Controller (reporting) |

## What's explicitly out of scope for this POC

This is a training *plan*, not delivered training — there are no real trainees, workshops, or quick-reference guides produced here, consistent with this project's no-real-users, no-overstated-capability rule (AGENTS.md). What exists instead is every phase's own `controls.md`/`README.md`, already written to be readable by someone learning the system, which is exactly what a real training programme would draw on rather than duplicate.
