import pandas as pd
from reconciliation_engine import reconcile_ap, reconcile_bank, reconcile_intercompany


# ---------------------------------------------------------------------------
# Bank
# ---------------------------------------------------------------------------

def test_reconcile_bank_exact_match():
    bank = pd.DataFrame([{
        "bank_transaction_id": "BANK-0001", "entity_id": "ENT-001", "currency": "GBP",
        "amount": 100.00, "transaction_date": "2026-06-05",
    }])
    payments = pd.DataFrame([{
        "payment_id": "PAY-0001", "entity_id": "ENT-001", "currency": "GBP",
        "amount": 100.00, "payment_date": "2026-06-03",
    }])
    results = reconcile_bank(bank, payments)
    assert len(results) == 1
    assert results[0].match_status == "matched"
    assert results[0].matched_id == "PAY-0001"


def test_reconcile_bank_probable_match_on_amount_variance():
    bank = pd.DataFrame([{
        "bank_transaction_id": "BANK-0001", "entity_id": "ENT-001", "currency": "GBP",
        "amount": 100.00, "transaction_date": "2026-06-05",
    }])
    payments = pd.DataFrame([{
        "payment_id": "PAY-0001", "entity_id": "ENT-001", "currency": "GBP",
        "amount": 101.50, "payment_date": "2026-06-05",  # 1.5% off -- within 2% loose tolerance
    }])
    results = reconcile_bank(bank, payments)
    assert results[0].match_status == "probable_match"
    assert results[0].matched_id == "PAY-0001"
    assert "amount differs" in results[0].exception_reason


def test_reconcile_bank_unmatched_when_nothing_close():
    bank = pd.DataFrame([{
        "bank_transaction_id": "BANK-0001", "entity_id": "ENT-001", "currency": "GBP",
        "amount": 100.00, "transaction_date": "2026-06-05",
    }])
    payments = pd.DataFrame([{
        "payment_id": "PAY-0001", "entity_id": "ENT-001", "currency": "GBP",
        "amount": 5000.00, "payment_date": "2026-06-05",
    }])
    results = reconcile_bank(bank, payments)
    assert results[0].match_status == "unmatched"
    assert results[0].matched_id is None


def test_reconcile_bank_tight_matches_are_claimed_before_probable():
    # Two bank transactions could both plausibly match the single exact
    # payment; the tight match should win it, leaving the other unmatched
    # rather than both landing on probable_match.
    bank = pd.DataFrame([
        {"bank_transaction_id": "BANK-0001", "entity_id": "ENT-001", "currency": "GBP", "amount": 101.00, "transaction_date": "2026-06-05"},
        {"bank_transaction_id": "BANK-0002", "entity_id": "ENT-001", "currency": "GBP", "amount": 100.00, "transaction_date": "2026-06-05"},
    ])
    payments = pd.DataFrame([
        {"payment_id": "PAY-0001", "entity_id": "ENT-001", "currency": "GBP", "amount": 100.00, "payment_date": "2026-06-05"},
    ])
    results = {r.subject_id: r for r in reconcile_bank(bank, payments)}
    assert results["BANK-0002"].match_status == "matched"
    assert results["BANK-0001"].match_status in ("probable_match", "unmatched")


# ---------------------------------------------------------------------------
# AP
# ---------------------------------------------------------------------------

def make_ap_invoice(**overrides):
    base = {
        "invoice_id": "INV-0001", "invoice_type": "AP", "entity_id": "ENT-001",
        "currency": "GBP", "amount": 500.00, "invoice_date": "2026-06-01",
    }
    base.update(overrides)
    return base


def make_payment(**overrides):
    base = {
        "payment_id": "PAY-0001", "entity_id": "ENT-001", "currency": "GBP",
        "amount": 500.00, "payment_type": "made", "payment_date": "2026-06-15", "invoice_id": None,
    }
    base.update(overrides)
    return base


def test_reconcile_ap_matches_exact_amount_within_window():
    invoices = pd.DataFrame([make_ap_invoice()])
    payments = pd.DataFrame([make_payment()])
    results = reconcile_ap(invoices, payments)
    assert results[0].match_status == "matched"
    assert results[0].matched_id == "PAY-0001"


def test_reconcile_ap_ignores_ar_invoices():
    invoices = pd.DataFrame([make_ap_invoice(invoice_type="AR", invoice_id="INV-0002")])
    payments = pd.DataFrame([make_payment()])
    results = reconcile_ap(invoices, payments)
    assert results == []


def test_reconcile_ap_unmatched_when_no_payment_in_window():
    invoices = pd.DataFrame([make_ap_invoice()])
    payments = pd.DataFrame([make_payment(payment_date="2026-12-01")])  # far outside the 90-day window
    results = reconcile_ap(invoices, payments)
    assert results[0].match_status == "unmatched"


def test_reconcile_ap_probable_match_on_partial_payment():
    invoices = pd.DataFrame([make_ap_invoice(amount=500.00)])
    payments = pd.DataFrame([make_payment(amount=495.00)])  # 1% off
    results = reconcile_ap(invoices, payments)
    assert results[0].match_status == "probable_match"
    assert "partial payment" in results[0].exception_reason


def test_reconcile_ap_flags_fk_mismatch_as_data_integrity_note():
    # The matched payment's own invoice_id points somewhere else entirely --
    # the independent match still finds it, but flags the disagreement.
    invoices = pd.DataFrame([make_ap_invoice()])
    payments = pd.DataFrame([make_payment(invoice_id="INV-9999-SOMETHING-ELSE")])
    results = reconcile_ap(invoices, payments)
    assert results[0].match_status == "matched"
    assert "data-integrity note" in results[0].exception_reason
    assert "INV-9999-SOMETHING-ELSE" in results[0].exception_reason


def test_reconcile_ap_no_fk_mismatch_note_when_link_agrees():
    invoices = pd.DataFrame([make_ap_invoice()])
    payments = pd.DataFrame([make_payment(invoice_id="INV-0001")])
    results = reconcile_ap(invoices, payments)
    assert results[0].match_status == "matched"
    assert results[0].exception_reason is None


# ---------------------------------------------------------------------------
# Intercompany
# ---------------------------------------------------------------------------

def test_reconcile_intercompany_matches_reversed_pair_same_period_and_amount():
    ic = pd.DataFrame([
        {"intercompany_transaction_id": "IC-0001", "entity_from_id": "ENT-001", "entity_to_id": "ENT-002",
         "reference": "REF-1", "amount": 1000.00, "currency": "GBP", "transaction_date": "2026-06-05"},
        {"intercompany_transaction_id": "IC-0002", "entity_from_id": "ENT-002", "entity_to_id": "ENT-001",
         "reference": "REF-1", "amount": 1000.00, "currency": "GBP", "transaction_date": "2026-06-06"},
    ])
    results = {r.subject_id: r for r in reconcile_intercompany(ic)}
    assert results["IC-0001"].match_status == "matched"
    assert results["IC-0002"].match_status == "matched"


def test_reconcile_intercompany_probable_match_on_period_difference():
    ic = pd.DataFrame([
        {"intercompany_transaction_id": "IC-0003", "entity_from_id": "ENT-001", "entity_to_id": "ENT-002",
         "reference": "REF-2", "amount": 1000.00, "currency": "GBP", "transaction_date": "2026-06-30"},
        {"intercompany_transaction_id": "IC-0004", "entity_from_id": "ENT-002", "entity_to_id": "ENT-001",
         "reference": "REF-2", "amount": 1000.00, "currency": "GBP", "transaction_date": "2026-07-02"},
    ])
    results = {r.subject_id: r for r in reconcile_intercompany(ic)}
    assert results["IC-0003"].match_status == "probable_match"
    assert "periods differ" in results["IC-0003"].exception_reason


def test_reconcile_intercompany_unmatched_when_no_counterpart_at_all():
    ic = pd.DataFrame([
        {"intercompany_transaction_id": "IC-0005", "entity_from_id": "ENT-001", "entity_to_id": "ENT-002",
         "reference": "REF-3", "amount": 1000.00, "currency": "GBP", "transaction_date": "2026-06-05"},
    ])
    results = reconcile_intercompany(ic)
    assert results[0].match_status == "unmatched"


def test_reconcile_intercompany_probable_match_on_amount_difference():
    ic = pd.DataFrame([
        {"intercompany_transaction_id": "IC-0006", "entity_from_id": "ENT-001", "entity_to_id": "ENT-002",
         "reference": "REF-4", "amount": 1000.00, "currency": "GBP", "transaction_date": "2026-06-05"},
        {"intercompany_transaction_id": "IC-0007", "entity_from_id": "ENT-002", "entity_to_id": "ENT-001",
         "reference": "REF-4", "amount": 850.00, "currency": "GBP", "transaction_date": "2026-06-05"},
    ])
    results = {r.subject_id: r for r in reconcile_intercompany(ic)}
    assert results["IC-0006"].match_status == "probable_match"
    assert "amount differs" in results["IC-0006"].exception_reason
