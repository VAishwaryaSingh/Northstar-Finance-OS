from invoice_classification import classify_vendor_account, requires_fx_conversion, validate_entity_ledger


def test_matching_account_is_confirmed_no_exception():
    result = classify_vendor_account("ACC-001", "ACC-001")
    assert result.matches_vendor_default is True
    assert result.exception is None
    assert result.suggested_account_id == "ACC-001"


def test_mismatched_account_is_flagged_not_silently_corrected():
    result = classify_vendor_account("ACC-001", "ACC-999")
    assert result.matches_vendor_default is False
    assert result.exception is not None
    assert "ACC-999" in result.exception
    assert "ACC-001" in result.exception
    # the suggestion is the vendor default -- but the actual account on
    # the invoice is left untouched by this function; it only flags
    assert result.suggested_account_id == "ACC-001"


def test_missing_invoice_account_suggests_vendor_default_no_exception():
    result = classify_vendor_account("ACC-001", None)
    assert result.suggested_account_id == "ACC-001"
    assert result.matches_vendor_default is True
    assert result.exception is None


def test_no_vendor_default_on_file_is_not_an_exception():
    result = classify_vendor_account(None, "ACC-999")
    assert result.suggested_account_id == "ACC-999"
    assert result.matches_vendor_default is True
    assert result.exception is None


def test_validate_entity_ledger_flags_missing_entity():
    assert validate_entity_ledger(None) is not None
    assert validate_entity_ledger("ENT-001") is None


def test_requires_fx_conversion_true_when_currencies_differ():
    assert requires_fx_conversion("USD", "GBP") is True


def test_requires_fx_conversion_false_when_currencies_match():
    assert requires_fx_conversion("GBP", "GBP") is False
