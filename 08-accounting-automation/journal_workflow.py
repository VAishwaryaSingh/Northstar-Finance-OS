"""Approval threshold and journal workflow rules (Phase 11, PLAN.md §23).

Formalises the "invoice amount -> approval threshold" rule that
05-sql/controls.sql could only leave as a placeholder assumption in a SQL
comment (there was nowhere else to put it yet). APPROVAL_THRESHOLD here is
now that rule's one authoritative definition in the codebase.

determine_journal_status is the workflow decision this rule exists to
drive: given an amount and who created/approved an entry, what status can
it actually land in? This still can't override schema.sql's own database
constraints (maker != checker, debit = credit) -- those remain the real
source of truth (07-api/README.md's "two layers of the same rule") -- this
just adds the threshold-aware decision neither the database nor the API's
Pydantic validation currently makes: an entry over threshold cannot reach
'posted' without a *different* approver on record, no matter how the
request got there.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# Documented assumption, not a real Northstar Health Group policy -- there
# isn't one yet (discovery-notes.md: "an informal approval threshold...
# isn't systematically enforced"). This constant is what enforces it.
APPROVAL_THRESHOLD = 10_000.00


@dataclass
class ApprovalRequirement:
    requires_approval: bool
    threshold: float
    reason: str


def approval_requirement(amount: float, threshold: float = APPROVAL_THRESHOLD) -> ApprovalRequirement:
    if amount >= threshold:
        return ApprovalRequirement(
            requires_approval=True, threshold=threshold,
            reason=f"amount {amount} meets or exceeds the {threshold} approval threshold",
        )
    return ApprovalRequirement(
        requires_approval=False, threshold=threshold,
        reason=f"amount {amount} is below the {threshold} approval threshold",
    )


@dataclass
class JournalWorkflowResult:
    status: str
    reason: str


def determine_journal_status(
    amount: float,
    created_by: str,
    approved_by: Optional[str],
    threshold: float = APPROVAL_THRESHOLD,
) -> JournalWorkflowResult:
    """Decide the furthest status this entry is allowed to reach right now.

    Doesn't re-check debit=credit or that approved_by != created_by --
    those are schema.sql's job (and 07-api/schemas.py's client-side
    mirror of them) -- this only adds the amount-aware rule neither of
    those checks: a below-threshold entry can post as soon as it has any
    valid approver (or none, if it's system-generated); an at-or-above-
    threshold entry needs a genuine, different approver on record before
    it can be marked posted at all.
    """
    requirement = approval_requirement(amount, threshold)

    if not requirement.requires_approval:
        if approved_by:
            return JournalWorkflowResult(status="posted", reason="below threshold, approver on record")
        return JournalWorkflowResult(status="pending_approval", reason="below threshold, awaiting any approver")

    if approved_by and approved_by != created_by:
        return JournalWorkflowResult(status="posted", reason=requirement.reason + "; distinct approver on record")

    return JournalWorkflowResult(
        status="pending_approval",
        reason=requirement.reason + "; requires a distinct approver before it can post",
    )
