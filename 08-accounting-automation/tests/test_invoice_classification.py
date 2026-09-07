from invoice_classification import (
    check_amount_outlier,
    classify_vendor_account,
    requires_fx_conversion,
    validate_entity_ledger,
)


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


def test_check_amount_outlier_flags_amount_far_outside_history():
    history = [100.0, 110.0, 95.0, 105.0, 90.0]
    result = check_amount_outlier(5000.0, history)
    assert result is not None
    assert "standard deviations" in result


def test_check_amount_outlier_passes_amount_within_normal_range():
    history = [100.0, 110.0, 95.0, 105.0, 90.0]
    result = check_amount_outlier(102.0, history)
    assert result is None


def test_check_amount_outlier_skips_when_history_too_short():
    # Fewer than MIN_HISTORY_FOR_OUTLIER_CHECK points -- not enough to
    # judge, so this is a "nothing to check against" pass, not a false pass.
    result = check_amount_outlier(5000.0, [100.0, 100.0])
    assert result is None


def test_check_amount_outlier_skips_when_no_history_at_all():
    assert check_amount_outlier(5000.0, None) is None
    assert check_amount_outlier(5000.0, []) is None


def test_check_amount_outlier_flags_any_deviation_from_a_constant_history():
    # every past invoice was exactly the same amount (stdev == 0) -- the
    # normal z-score formula would divide by zero, handled as a special case
    result = check_amount_outlier(150.0, [100.0, 100.0, 100.0])
    assert result is not None
    assert "constant historical amount" in result


def test_check_amount_outlier_does_not_flag_the_constant_amount_itself():
    result = check_amount_outlier(100.0, [100.0, 100.0, 100.0])
    assert result is None
