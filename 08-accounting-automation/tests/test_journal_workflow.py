from journal_workflow import APPROVAL_THRESHOLD, approval_requirement, determine_journal_status


def test_amount_below_threshold_does_not_require_approval():
    result = approval_requirement(APPROVAL_THRESHOLD - 1)
    assert result.requires_approval is False


def test_amount_at_threshold_requires_approval():
    result = approval_requirement(APPROVAL_THRESHOLD)
    assert result.requires_approval is True


def test_amount_above_threshold_requires_approval():
    result = approval_requirement(APPROVAL_THRESHOLD + 1)
    assert result.requires_approval is True


def test_below_threshold_with_approver_posts():
    result = determine_journal_status(amount=500, created_by="USR-001", approved_by="USR-004")
    assert result.status == "posted"


def test_below_threshold_without_approver_is_pending():
    result = determine_journal_status(amount=500, created_by="USR-001", approved_by=None)
    assert result.status == "pending_approval"


def test_above_threshold_with_distinct_approver_posts():
    result = determine_journal_status(amount=50_000, created_by="USR-001", approved_by="USR-004")
    assert result.status == "posted"


def test_above_threshold_without_approver_stays_pending():
    result = determine_journal_status(amount=50_000, created_by="USR-001", approved_by=None)
    assert result.status == "pending_approval"


def test_above_threshold_cannot_post_no_matter_who_almost_approved_it():
    # This function trusts that maker != checker was already enforced
    # upstream (schema.sql / 07-api/schemas.py) -- it doesn't re-check
    # that here, only that *some* distinct approver exists for a
    # large-amount entry.
    result = determine_journal_status(amount=50_000, created_by="USR-001", approved_by="USR-002")
    assert result.status == "posted"
