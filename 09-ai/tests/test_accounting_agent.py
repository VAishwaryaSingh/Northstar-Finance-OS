import pytest
from accounting_agent import override_recommendation, process_invoice
from llm_client import LLMSuggestion, MockLLMClient

KNOWN_ACCOUNTS = ["ACC-001", "ACC-002"]
KNOWN_ENTITIES = ["ENT-001", "ENT-002"]


def make_invoice(invoice_id="INV-0001", **overrides):
    base = {"invoice_id": invoice_id, "invoice_type": "AP", "amount": 500.0, "currency": "GBP"}
    base.update(overrides)
    return base


# --- The six PLAN.md §30 AI test categories -------------------------------

def test_high_confidence_correct_case_does_not_require_review():
    invoice = make_invoice()
    suggestion = LLMSuggestion("Medical Supplies Ltd", "ACC-001", "ENT-001", 0.97, "matches vendor default")
    client = MockLLMClient({invoice["invoice_id"]: suggestion})

    result = process_invoice(invoice, client, KNOWN_ACCOUNTS, KNOWN_ENTITIES,
                              vendor_default_account_code="ACC-001", amount=500.0, audit_sample_rate=0.0)

    assert result.requires_human_review is False
    assert result.review_reasons == []


def test_low_confidence_case_requires_review():
    invoice = make_invoice()
    suggestion = LLMSuggestion("Unclear Vendor Ltd", "ACC-001", "ENT-001", 0.60, "uncertain match")
    client = MockLLMClient({invoice["invoice_id"]: suggestion})

    result = process_invoice(invoice, client, KNOWN_ACCOUNTS, KNOWN_ENTITIES,
                              vendor_default_account_code="ACC-001", amount=500.0)

    assert result.requires_human_review is True
    assert any("confidence" in r for r in result.review_reasons)


def test_ambiguous_vendor_conflicting_with_deterministic_rule_requires_review():
    # The AI suggests a different account than the vendor's known default --
    # exactly the "incorrect account mapping" case Phase 11 already flags
    # on real data. High model confidence does not override this.
    invoice = make_invoice()
    suggestion = LLMSuggestion("Vantage Software Solutions", "ACC-002", "ENT-001", 0.96, "looks like a software cost")
    client = MockLLMClient({invoice["invoice_id"]: suggestion})

    result = process_invoice(invoice, client, KNOWN_ACCOUNTS, KNOWN_ENTITIES,
                              vendor_default_account_code="ACC-001", amount=500.0)

    assert result.requires_human_review is True
    assert any("deterministic check failed" in r for r in result.review_reasons)


def test_missing_data_case_with_no_vendor_history_yields_low_confidence_and_review():
    # No vendor_default_account_code on file at all -- simulates a genuinely
    # new vendor. A model that's honest about missing data should reflect
    # that as low confidence rather than guessing with false certainty.
    invoice = make_invoice()
    suggestion = LLMSuggestion("Brand New Vendor Inc", "ACC-001", "ENT-001", 0.40, "no prior history for this vendor")
    client = MockLLMClient({invoice["invoice_id"]: suggestion})

    result = process_invoice(invoice, client, KNOWN_ACCOUNTS, KNOWN_ENTITIES,
                              vendor_default_account_code=None, amount=None)

    assert result.requires_human_review is True
    assert any("confidence" in r for r in result.review_reasons)


def test_adversarial_hallucinated_account_forces_review_even_at_high_confidence():
    # The core safety guarantee: a confident-sounding but fabricated
    # account code must never slip through just because confidence is high.
    invoice = make_invoice()
    suggestion = LLMSuggestion("Some Vendor", "ACC-999-DOES-NOT-EXIST", "ENT-001", 0.99, "very sure")
    client = MockLLMClient({invoice["invoice_id"]: suggestion})

    result = process_invoice(invoice, client, KNOWN_ACCOUNTS, KNOWN_ENTITIES,
                              vendor_default_account_code="ACC-001", amount=500.0)

    assert result.requires_human_review is True
    assert any("not a real account code" in r for r in result.review_reasons)


def test_nonsensical_entity_code_also_forces_review():
    invoice = make_invoice()
    suggestion = LLMSuggestion("Some Vendor", "ACC-001", "ENT-DOES-NOT-EXIST", 0.99, "very sure")
    client = MockLLMClient({invoice["invoice_id"]: suggestion})

    result = process_invoice(invoice, client, KNOWN_ACCOUNTS, KNOWN_ENTITIES,
                              vendor_default_account_code="ACC-001", amount=500.0)

    assert result.requires_human_review is True
    assert any("not a real entity code" in r for r in result.review_reasons)


# --- Approval threshold (reused from Phase 11, not reimplemented) ---------

def test_amount_above_approval_threshold_requires_review_even_with_perfect_match():
    invoice = make_invoice(amount=50_000.0)
    suggestion = LLMSuggestion("Medical Supplies Ltd", "ACC-001", "ENT-001", 0.99, "perfect match")
    client = MockLLMClient({invoice["invoice_id"]: suggestion})

    result = process_invoice(invoice, client, KNOWN_ACCOUNTS, KNOWN_ENTITIES,
                              vendor_default_account_code="ACC-001", amount=50_000.0)

    assert result.requires_human_review is True
    assert any("transaction requirement" in r for r in result.review_reasons)


def test_amount_below_threshold_with_everything_else_clean_does_not_require_review():
    invoice = make_invoice(amount=100.0)
    suggestion = LLMSuggestion("Medical Supplies Ltd", "ACC-001", "ENT-001", 0.99, "perfect match")
    client = MockLLMClient({invoice["invoice_id"]: suggestion})

    result = process_invoice(invoice, client, KNOWN_ACCOUNTS, KNOWN_ENTITIES,
                              vendor_default_account_code="ACC-001", amount=100.0, audit_sample_rate=0.0)

    assert result.requires_human_review is False


# --- Override with mandatory reason ---------------------------------------

def test_override_requires_a_non_blank_reason():
    invoice = make_invoice()
    suggestion = LLMSuggestion("V", "ACC-001", "ENT-001", 0.5, "r")
    client = MockLLMClient({invoice["invoice_id"]: suggestion})
    recommendation = process_invoice(invoice, client, KNOWN_ACCOUNTS, KNOWN_ENTITIES)

    with pytest.raises(ValueError):
        override_recommendation(recommendation, overridden_by="USR-004", reason="")

    with pytest.raises(ValueError):
        override_recommendation(recommendation, overridden_by="USR-004", reason="   ")


# --- The two controls added after Phase 12's evaluation surfaced a gap ---

def test_amount_far_outside_vendor_history_requires_review_even_with_perfect_match():
    invoice = make_invoice(amount=9000.0)
    suggestion = LLMSuggestion("Medical Supplies Ltd", "ACC-001", "ENT-001", 0.99, "matches vendor default")
    client = MockLLMClient({invoice["invoice_id"]: suggestion})
    history = [100.0, 110.0, 95.0, 105.0, 90.0]

    result = process_invoice(invoice, client, KNOWN_ACCOUNTS, KNOWN_ENTITIES,
                              vendor_default_account_code="ACC-001", amount=9000.0,
                              vendor_historical_amounts=history, audit_sample_rate=0.0)

    assert result.requires_human_review is True
    assert any("amount outlier" in r for r in result.review_reasons)


def test_amount_within_vendor_history_is_not_flagged_as_outlier():
    invoice = make_invoice(amount=102.0)
    suggestion = LLMSuggestion("Medical Supplies Ltd", "ACC-001", "ENT-001", 0.99, "matches vendor default")
    client = MockLLMClient({invoice["invoice_id"]: suggestion})
    history = [100.0, 110.0, 95.0, 105.0, 90.0]

    result = process_invoice(invoice, client, KNOWN_ACCOUNTS, KNOWN_ENTITIES,
                              vendor_default_account_code="ACC-001", amount=102.0,
                              vendor_historical_amounts=history, audit_sample_rate=0.0)

    assert result.requires_human_review is False


def test_audit_sample_rate_one_always_forces_review_even_when_everything_else_is_clean():
    invoice = make_invoice(amount=50.0)
    suggestion = LLMSuggestion("Medical Supplies Ltd", "ACC-001", "ENT-001", 0.99, "matches vendor default")
    client = MockLLMClient({invoice["invoice_id"]: suggestion})

    result = process_invoice(invoice, client, KNOWN_ACCOUNTS, KNOWN_ENTITIES,
                              vendor_default_account_code="ACC-001", amount=50.0,
                              audit_sample_rate=1.0)

    assert result.requires_human_review is True
    assert any("audit sample" in r for r in result.review_reasons)


def test_audit_sample_rate_zero_never_adds_a_sampling_reason():
    invoice = make_invoice(amount=50.0)
    suggestion = LLMSuggestion("Medical Supplies Ltd", "ACC-001", "ENT-001", 0.99, "matches vendor default")
    client = MockLLMClient({invoice["invoice_id"]: suggestion})

    result = process_invoice(invoice, client, KNOWN_ACCOUNTS, KNOWN_ENTITIES,
                              vendor_default_account_code="ACC-001", amount=50.0,
                              audit_sample_rate=0.0)

    assert result.requires_human_review is False
    assert result.review_reasons == []


def test_override_with_a_reason_succeeds_and_records_it():
    invoice = make_invoice()
    suggestion = LLMSuggestion("V", "ACC-001", "ENT-001", 0.5, "r")
    client = MockLLMClient({invoice["invoice_id"]: suggestion})
    recommendation = process_invoice(invoice, client, KNOWN_ACCOUNTS, KNOWN_ENTITIES)

    record = override_recommendation(recommendation, overridden_by="USR-004", reason="Confirmed correct with the vendor directly.")
    assert record.reason == "Confirmed correct with the vendor directly."
    assert record.overridden_by == "USR-004"
    assert record.invoice_id == invoice["invoice_id"]
