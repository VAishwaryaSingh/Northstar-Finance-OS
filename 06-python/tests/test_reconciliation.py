import pandas as pd
from reconciliation import flag_duplicate_invoices, match_intercompany, match_transactions


def test_flag_duplicate_invoices_keeps_first_flags_rest():
    df = pd.DataFrame([
        {"invoice_id": "INV-0001", "entity_id": "ENT-001", "invoice_number": "NHH-AR-1", "invoice_type": "AR", "status": "open"},
        {"invoice_id": "INV-0099", "entity_id": "ENT-001", "invoice_number": "NHH-AR-1", "invoice_type": "AR", "status": "open"},
        {"invoice_id": "INV-0002", "entity_id": "ENT-001", "invoice_number": "NHH-AR-2", "invoice_type": "AR", "status": "open"},
    ])
    result = flag_duplicate_invoices(df)

    first = result[result["invoice_id"] == "INV-0001"].iloc[0]
    dup = result[result["invoice_id"] == "INV-0099"].iloc[0]
    unique = result[result["invoice_id"] == "INV-0002"].iloc[0]

    assert first["status"] == "open"
    assert first["duplicate_of"] is None
    assert dup["status"] == "duplicate_flagged"
    assert dup["duplicate_of"] == "INV-0001"
    assert unique["status"] == "open"
    assert unique["duplicate_of"] is None


def test_flag_duplicate_invoices_does_not_flag_different_entities_or_types():
    # same invoice_number is fine across entities/types -- discovery-notes.md
    # notes invoice numbers are legitimately reused across entities
    df = pd.DataFrame([
        {"invoice_id": "INV-0001", "entity_id": "ENT-001", "invoice_number": "1001", "invoice_type": "AR", "status": "open"},
        {"invoice_id": "INV-0002", "entity_id": "ENT-002", "invoice_number": "1001", "invoice_type": "AR", "status": "open"},
        {"invoice_id": "INV-0003", "entity_id": "ENT-001", "invoice_number": "1001", "invoice_type": "AP", "status": "open"},
    ])
    result = flag_duplicate_invoices(df)
    assert (result["status"] == "open").all()


def test_match_transactions_matches_exact_amount_and_close_date():
    bank = pd.DataFrame([
        {"bank_transaction_id": "BANK-0001", "entity_id": "ENT-001", "currency": "GBP",
         "amount": 100.00, "transaction_date": "2026-06-05"},
    ])
    payments = pd.DataFrame([
        {"payment_id": "PAY-0001", "entity_id": "ENT-001", "currency": "GBP",
         "amount": 100.00, "payment_date": "2026-06-03"},
    ])
    matches, unmatched = match_transactions(bank, payments)
    assert len(matches) == 1
    assert matches.iloc[0]["bank_transaction_id"] == "BANK-0001"
    assert matches.iloc[0]["payment_id"] == "PAY-0001"
    assert unmatched.empty


def test_match_transactions_leaves_transactions_with_no_candidate_unmatched():
    bank = pd.DataFrame([
        {"bank_transaction_id": "BANK-0001", "entity_id": "ENT-001", "currency": "GBP",
         "amount": 250.00, "transaction_date": "2026-06-05"},
    ])
    payments = pd.DataFrame([
        {"payment_id": "PAY-0001", "entity_id": "ENT-001", "currency": "GBP",
         "amount": 100.00, "payment_date": "2026-06-03"},
    ])
    matches, unmatched = match_transactions(bank, payments)
    assert matches.empty
    assert len(unmatched) == 1
    assert unmatched.iloc[0]["bank_transaction_id"] == "BANK-0001"


def test_match_transactions_respects_day_tolerance():
    bank = pd.DataFrame([
        {"bank_transaction_id": "BANK-0001", "entity_id": "ENT-001", "currency": "GBP",
         "amount": 100.00, "transaction_date": "2026-06-20"},  # 17 days after payment
    ])
    payments = pd.DataFrame([
        {"payment_id": "PAY-0001", "entity_id": "ENT-001", "currency": "GBP",
         "amount": 100.00, "payment_date": "2026-06-03"},
    ])
    matches, unmatched = match_transactions(bank, payments, day_tolerance=3)
    assert matches.empty
    assert len(unmatched) == 1


def test_match_intercompany_matches_reciprocal_pair_with_same_amount():
    ic = pd.DataFrame([
        {"intercompany_transaction_id": "IC-0001", "reference": "IC-REF-1", "amount": 5000.00},
        {"intercompany_transaction_id": "IC-0002", "reference": "IC-REF-1", "amount": 5000.00},
    ])
    matched, unmatched = match_intercompany(ic)
    assert len(matched) == 2
    assert unmatched.empty


def test_match_intercompany_flags_single_sided_reference_as_unmatched():
    ic = pd.DataFrame([
        {"intercompany_transaction_id": "IC-0003", "reference": "IC-REF-2", "amount": 5000.00},
    ])
    matched, unmatched = match_intercompany(ic)
    assert matched.empty
    assert len(unmatched) == 1


def test_match_intercompany_flags_amount_mismatch_as_unmatched():
    ic = pd.DataFrame([
        {"intercompany_transaction_id": "IC-0004", "reference": "IC-REF-3", "amount": 5000.00},
        {"intercompany_transaction_id": "IC-0005", "reference": "IC-REF-3", "amount": 4800.00},
    ])
    matched, unmatched = match_intercompany(ic)
    assert matched.empty
    assert len(unmatched) == 2
