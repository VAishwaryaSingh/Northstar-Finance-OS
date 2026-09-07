# Demo Script — Northstar Finance OS

A 10-minute solutions-consulting demo, following PLAN.md §34's structure exactly. Every `[SHOW: ...]` cue points to a real, working artifact in this repository — nothing here is a mockup or a placeholder screenshot. See [demo-flow.md](./demo-flow.md) for the technical run-of-show (what to have open, in what order) and [discovery-demo.md](./discovery-demo.md) for why this structure is deliberate, not just a features tour.

---

## 0:00–1:00 — Customer problem

> "Sarah, David, Grace — thanks for the time. Before I show you anything, let me play back what you told me, because I want you to stop me if I've got this wrong.
>
> Close takes **12 business days**. Roughly **70% of your journals are manual**. Bank reconciliation is **~80% manual work**. You're carrying **~35 unresolved intercompany exceptions a month**. Management reporting takes **~2 days** to assemble by hand from Excel exports. And when the board asks for cash position or a large intercompany movement, you can't answer same-day — you have to go and ask Shared Services to go and check.
>
> None of that is a knowledge problem. Your team knows accounting. It's a data-movement problem — every handoff between billing, banking, AP, and your ERP is manual and unvalidated. That's the actual thing we're going to fix today."

**[SHOW: nothing yet — this is a verbal recap, eye contact, not a screen]**

---

## 1:00–2:00 — Discovery recap

> "Here's the current-state process, mapped exactly as your team described it."

**[SHOW: `02-process-mapping/current-state.md` — the ASCII flow: Billing → CSV/Manual Export → Excel → Legacy ERP → Finance Team → Manual Reconciliation → Manual Journals → Intercompany Matching → Reporting Workbook → PowerPoint → CFO]**

> "Five things stand out, and they're the five things this demo is going to solve, in this order: **close** (12 days), **reconciliations** (80% manual), **intercompany** (35 exceptions/month), **reporting** (2 days), and **controls** — there's no system of record for who approved what, and posted entries can be edited with no audit trail.
>
> The root cause is the same across all five: validation and matching only exist in people's heads and spreadsheets, applied downstream, over and over, instead of once, at the point data enters the system."

**[SHOW: `02-process-mapping/process-analysis.md`'s "Why this ordering matters" — one sentence, on screen]**

---

## 2:00–3:00 — Architecture

> "So the target design does one thing structurally differently: validation happens once, at ingestion, not repeatedly downstream."

**[SHOW: `03-architecture/system-architecture.md`'s diagram — Sources → Integration → Core → AI → Controls → Outputs]**

> "Billing, banking, AP, and your existing ERP all feed into one integration layer — API where the source has one, file ingestion everywhere else. Everything lands in one finance data model, one shared chart of accounts across all three entities instead of three that have drifted apart. Deterministic rules classify what they can. AI only touches what the rules can't resolve, and never bypasses a control — that's not a slogan, I'll show you the actual code enforcing it in a few minutes. Everything's logged. Nothing gets deleted, only corrected with a reason."

---

## 3:00–5:00 — Data / integration

> "Let's make this real. Here's a raw AP invoice, exactly as it would arrive by email as a PDF today."

**[SHOW: a row from `04-data/invoices.csv` — an AP invoice where `vendor_name_raw` is `"Med Supplies Ltd"`, not the vendor master's `"Medical Supplies Ltd"`]**

> "That's a real, common problem — the vendor name doesn't exactly match your master list. Today, that either gets manually corrected or, more often, doesn't get caught until someone's chasing a payment. Here's what happens when it's ingested."

**[SHOW: run `.venv/bin/python 06-python/ingestion.py` live, or `06-python/exception-report.md`'s "Vendor Resolved By Fuzzy Match" section]**

> "Fuzzy name matching resolves it automatically — recovers invoices a plain database join would have to drop. Where it can't resolve something — say, a missing entity code — it doesn't guess. It logs why, and holds it for review."

**[SHOW: `06-python/exception-report.md`'s "Missing Entity Code" section]**

> "And here's the same thing from the other direction — an API request creating an invoice."

**[SHOW: a `POST /invoices` call via `07-api`'s Swagger UI at `/docs`, or the curl example in `07-api/README.md`]**

> "Send the same invoice twice by accident — a network retry, a double-click — and it doesn't create a duplicate. It recognises it and hands you back the original."

---

## 5:00–7:00 — Accounting automation

> "Now the part that matters most for trust: classification and control."

**[SHOW: `08-accounting-automation/rule-findings.md`'s "Incorrect Account Mapping" section — invoice `INV-0046`, Apex Facilities Management]**

> "This vendor almost always codes to Facilities Expense. This particular invoice was coded differently. The system doesn't silently fix that — it flags it, because a person might have had a legitimate reason. That's the same principle everywhere: detect, don't silently correct.
>
> For genuinely ambiguous cases — not 'wrong', just unclear — that's where AI assists."

**[SHOW: `09-ai/evaluation-results.md`, specifically the row where confidence is high but the account still gets flagged for review, or `09-ai/prompts.md`'s example output shape]**

> "The AI suggests, with a confidence score and its reasoning. If confidence is below 95%, if it disagrees with the deterministic rule, if it references an account or entity that doesn't actually exist, or if the amount is a statistical outlier against that vendor's own history — any one of those routes it to a human. No exceptions, no override by confidence. I evaluated this against 11 test cases, including deliberately adversarial ones — a model claiming 99% confidence in a completely fabricated account code — and it was still caught."

**[SHOW: `09-ai/evaluation.md` — specifically the honest discussion of the one case that wasn't caught]**

> "And I'll be straight with you: it's not perfect. One case in my evaluation set — everything about it looked right, and it wasn't — got through. That's not a flaw I'm hiding; it's the reason we also randomly sample a small percentage of even the 'clean' auto-approved transactions. No system catches everything on the first pass. The question is whether you know your residual risk or you're assuming it's zero."

---

## 7:00–8:30 — Reconciliation / close dashboard

> "Here's what your Controller sees, live, right now."

**[SHOW: `10-dashboard/app.py` running — `.venv/bin/streamlit run 10-dashboard/app.py`]**

> "Close progress by entity and period, not a status someone has to ask about. Unapproved journals, with amounts, not just a count. Overdue AP. Unreconciled cash — the actual amount sitting outstanding, not just a transaction count. Intercompany exceptions, live — this is your ~35-a-month problem, visible the moment it happens instead of discovered at month-end.
>
> And this row — 'AI recommendations awaiting review' — isn't a stale report. It's running the same account-mapping rule live, right now, against your actual data, every time this page loads."

---

## 8:30–9:30 — CFO outcome

> "Tie this back to what you told me in the first minute."

**[SHOW: a simple before/after, spoken or on a slide — no new artifact needed]**

| | Today | Target |
|---|---|---|
| Close | 12 days | ≤7 days (R01) |
| Manual reconciliation | ~80% | ≤20% (R02) |
| Intercompany exceptions | ~35/month | ≤10/month (R04) |
| Reporting assembly | ~2 days | <4 hours (R05) |
| Journal traceability | Inconsistent (email/paper) | 100%, system-enforced (R06) |

> "Every one of those targets is in the requirements document we built from your own discovery answers — I'm not asking you to trust a vendor's marketing claim, I'm showing you the same numbers you gave me, with a specific mechanism against each one."

---

## 9:30–10:00 — Implementation

> "None of this is big-bang. We pilot on one entity — Shared Services Ltd, GBP-only, no FX complexity, and it's the team that will use this daily, so they're the first to benefit, not the last. One full close cycle, legacy system stays live in parallel, we validate both agree before we retire anything for that entity. Then Holdings Ltd. Then Health Services Inc last, deliberately, because that's the first entity where FX conversion runs for real, not just on intercompany. Roughly 9 to 13 weeks for the full rollout once migration's ready, on top of what we've already discussed for build and testing."

**[SHOW: `12-implementation/rollout-plan.md`'s schedule table]**

> "Full implementation and migration plan is written up, including the risk register and exactly what gets tested before each entity goes live. Happy to walk through it in detail whenever makes sense."

---

**End of demo.**
