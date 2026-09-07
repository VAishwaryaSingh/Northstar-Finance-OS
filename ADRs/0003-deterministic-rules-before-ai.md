# ADR-0003: Deterministic rules before AI

## Context

[future-state.md](../02-process-mapping/future-state.md) states the critical design principle that "AI should assist accounting decisions but must not bypass accounting controls." PLAN.md §9 makes this a build-order requirement: the data model, ingestion pipeline, and reconciliation engine (all deterministic) are built before any AI component (Phase 12). This ADR formalises that principle as an architecture decision rather than leaving it implicit.

## Options considered

- **AI-first classification** — route ambiguous and unambiguous transactions alike through an AI classifier, on the theory that a good model handles both; faster to build a flashy demo, but risks non-deterministic behaviour on cases that have a single objectively correct answer, and is exactly the anti-pattern PLAN.md §18 warns against ("do not build a simplistic 'AI says debit / credit' demo without modelling the underlying accounting objects")
- **Deterministic rules only, no AI** — fully predictable and auditable, but doesn't demonstrate the AI-native capability this project exists to showcase, and leaves genuinely ambiguous cases (the ones that actually cost close-cycle time) unaddressed
- **Deterministic rules first; AI only for what the rules can't resolve** — rules handle vendor→account, entity→ledger, currency→FX, and duplicate/missing-field detection (PLAN.md §23); AI is invoked only on the residual ambiguous cases, always producing a confidence score and evidence, and is routed to human review below a threshold or on a failed control check (PLAN.md §25)

## Decision

Deterministic rules run first and resolve everything they can. AI is invoked only for classification that deterministic rules cannot resolve, and every AI output carries a confidence score and supporting evidence. AI recommendations that fail a control check or fall below the confidence threshold are routed to human review — never auto-posted, regardless of confidence.

## Trade-offs

- This is more conservative than an "AI does everything" demo, and produces a less flashy AI showcase — but a finance/audit-literate reviewer (the actual target audience for this portfolio project) will trust a system that is deterministic-first and AI-assisted far more than one that lets a model post journals unsupervised
- Requires building the full deterministic layer (data model, rules engine) before the AI component has anything meaningful to sit on top of, which is why AI is Phase 12 of 18 rather than an early phase

## Consequences

- `08-accounting-automation/` (Phase 11) is built and functioning before `09-ai/accounting_agent.py` (Phase 12) is started
- The AI evaluation in Phase 12 (PLAN.md §31) explicitly measures **unsafe automation rate** — the frequency with which AI output would have bypassed a control if not for the human-in-the-loop gate — as a first-class metric, not an afterthought
