"""AI accounting assistant (Phase 12, PLAN.md §24-25).

    Invoice -> Extract fields -> Identify vendor -> Suggest entity ->
    Suggest account -> Confidence score -> Evidence/reasoning ->
    Control checks -> Human approval -> Post

Unlike Phase 11's exception_rules.py (which deliberately reimplements small
pieces of 06-python's logic rather than cross-importing -- see its own
controls.md), this module *does* import 08-accounting-automation directly.
That's not an inconsistency: PLAN.md's critical distinction is that the AI
must be checked by the *same* deterministic rules every other posting path
uses, not a second copy of them that could quietly drift out of sync. The
one thing an AI safety boundary cannot be is "close enough."

Both directories are invalid Python package names (leading digit), so the
import below uses the same sys.path trick as every other cross-phase
script in this project (06-python/tests/conftest.py, etc.) -- just doing
it from a script file instead of a conftest.py.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "08-accounting-automation"))

from invoice_classification import check_amount_outlier, classify_vendor_account  # noqa: E402
from journal_workflow import APPROVAL_THRESHOLD, approval_requirement  # noqa: E402
from exception_rules import DEFAULT_AUDIT_SAMPLE_RATE, should_sample_for_audit  # noqa: E402

from llm_client import LLMClient, LLMSuggestion  # noqa: E402

# PLAN.md §25's example policy, implemented (not just documented) here.
CONFIDENCE_THRESHOLD = 0.95


@dataclass
class AIRecommendation:
    invoice_id: str
    vendor_identified: str
    suggested_account_code: str
    suggested_entity_code: str
    confidence: float
    reasoning: str
    requires_human_review: bool
    review_reasons: list[str] = field(default_factory=list)


def build_prompt(invoice: dict, known_accounts: list[str], known_entities: list[str]) -> str:
    """Extract-fields step. Only ever gives the model information that
    actually came from the invoice or the reference data -- this is what
    makes "no hallucinated accounting data" enforceable downstream (see
    validate_suggestion): the model is never given room to need to invent
    an account or entity, because every valid option is listed explicitly.
    """
    return (
        f"Invoice {invoice['invoice_id']} ({invoice['invoice_type']}).\n"
        f"Vendor name as received: {invoice.get('vendor_name_raw', 'unknown')!r}\n"
        f"Amount: {invoice['amount']} {invoice['currency']}\n"
        f"Account currently on the invoice: {invoice.get('account_code', 'none')!r}\n"
        f"Reason this needed review: {invoice.get('review_reason', 'not specified')}\n"
        f"Valid account codes: {', '.join(known_accounts)}\n"
        f"Valid entity codes: {', '.join(known_entities)}\n"
        "Suggest the correct account and entity, with your confidence and reasoning. "
        "Only use the account/entity codes listed above -- never invent one."
    )


def validate_suggestion(suggestion: LLMSuggestion, known_accounts: list[str], known_entities: list[str]) -> list[str]:
    """No-hallucinated-data check: the model's suggestion must reference
    real codes, not ones it made up. Returns a list of problems (empty if
    clean) -- any problem here forces human review regardless of the
    model's own confidence score, because a confident hallucination is
    exactly what this check exists to catch."""
    problems = []
    if suggestion.suggested_account_code not in known_accounts:
        problems.append(f"suggested account {suggestion.suggested_account_code!r} is not a real account code")
    if suggestion.suggested_entity_code not in known_entities:
        problems.append(f"suggested entity {suggestion.suggested_entity_code!r} is not a real entity code")
    return problems


def process_invoice(
    invoice: dict,
    llm_client: LLMClient,
    known_accounts: list[str],
    known_entities: list[str],
    vendor_default_account_code: Optional[str] = None,
    amount: Optional[float] = None,
    approval_threshold: float = APPROVAL_THRESHOLD,
    vendor_historical_amounts: Optional[list[float]] = None,
    audit_sample_rate: float = DEFAULT_AUDIT_SAMPLE_RATE,
) -> AIRecommendation:
    """Runs one invoice through the full pipeline, ending in a
    recommendation that has already had every PLAN.md §25 control check
    applied -- by the time this returns, requires_human_review is the
    final word, not a suggestion the caller still has to double-check.
    """
    prompt = build_prompt(invoice, known_accounts, known_entities)
    suggestion = llm_client.classify_invoice(prompt)

    review_reasons: list[str] = []

    # 1. No hallucinated data (§25) -- checked first: a hallucinated
    #    suggestion can't even be meaningfully scored against the other
    #    checks below.
    review_reasons += validate_suggestion(suggestion, known_accounts, known_entities)

    # 2. Deterministic validation (§25) -- the AI's suggestion is checked
    #    by the exact same rule real invoices are checked by (Phase 11),
    #    not a parallel opinion. A mismatch here means Phase 11 itself
    #    would flag this invoice even if a human manually re-entered the
    #    AI's suggestion -- the AI doesn't get a pass that a person wouldn't.
    if vendor_default_account_code is not None:
        mapping_result = classify_vendor_account(vendor_default_account_code, suggestion.suggested_account_code)
        if mapping_result.exception:
            review_reasons.append(f"deterministic check failed: {mapping_result.exception}")

    # 3. Confidence threshold (§25).
    if suggestion.confidence < CONFIDENCE_THRESHOLD:
        review_reasons.append(f"confidence {suggestion.confidence} is below the {CONFIDENCE_THRESHOLD} threshold")

    # 4. Approval threshold (§25) -- reuses Phase 11's rule, not a new number.
    if amount is not None:
        requirement = approval_requirement(amount, approval_threshold)
        if requirement.requires_approval:
            review_reasons.append(f"transaction requirement: {requirement.reason}")

    # 5. Amount-outlier check -- catches a vendor's invoice being far
    #    outside their own historical range, even when the account matches
    #    and confidence is high. Added after evaluation surfaced that
    #    checks 1-4 alone can all pass on a transaction that's still wrong
    #    (see evaluation.md's EVAL-010 discussion) -- this closes part of
    #    that gap, not all of it.
    if amount is not None:
        outlier_issue = check_amount_outlier(amount, vendor_historical_amounts)
        if outlier_issue:
            review_reasons.append(f"amount outlier: {outlier_issue}")

    # 6. Audit sampling -- the honest answer to the part of the gap check 5
    #    still can't close: a transaction that is a genuine anomaly but
    #    matches nothing else on file. No per-transaction rule can catch
    #    that with certainty, so a fraction of the otherwise-clean
    #    population is sampled for review regardless of what else passed.
    #    This does not guarantee catching any *specific* transaction --
    #    only that the auto-approved population isn't 100% unreviewed.
    if should_sample_for_audit(invoice["invoice_id"], audit_sample_rate):
        review_reasons.append(f"selected for random audit sample (rate={audit_sample_rate})")

    return AIRecommendation(
        invoice_id=invoice["invoice_id"],
        vendor_identified=suggestion.vendor_identified,
        suggested_account_code=suggestion.suggested_account_code,
        suggested_entity_code=suggestion.suggested_entity_code,
        confidence=suggestion.confidence,
        reasoning=suggestion.reasoning,
        requires_human_review=len(review_reasons) > 0,
        review_reasons=review_reasons,
    )


@dataclass
class OverrideRecord:
    invoice_id: str
    overridden_by: str
    reason: str
    original_recommendation: AIRecommendation


def override_recommendation(recommendation: AIRecommendation, overridden_by: str, reason: str) -> OverrideRecord:
    """Ability to override + reason for override (§25). A blank reason is
    rejected outright -- matching schema.sql's audit_logs CHECK constraint
    that an 'override' action always carries a reason, not just documented
    policy that a human could skip in a hurry."""
    if not reason or not reason.strip():
        raise ValueError("an override must be given a reason -- this is a hard requirement, not a suggestion")
    return OverrideRecord(
        invoice_id=recommendation.invoice_id,
        overridden_by=overridden_by,
        reason=reason.strip(),
        original_recommendation=recommendation,
    )
