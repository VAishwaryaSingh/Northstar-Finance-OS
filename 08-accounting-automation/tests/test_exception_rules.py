from exception_rules import check_duplicate_invoices, check_intercompany_counterpart, check_required_fields


def test_check_duplicate_invoices_flags_the_second_occurrence():
    invoices = [
        {"invoice_id": "INV-0001", "entity_id": "ENT-001", "invoice_number": "N1", "invoice_type": "AR"},
        {"invoice_id": "INV-0099", "entity_id": "ENT-001", "invoice_number": "N1", "invoice_type": "AR"},
    ]
    exceptions = check_duplicate_invoices(invoices)
    assert len(exceptions) == 1
    assert exceptions[0].rule == "duplicate_invoice"
    assert exceptions[0].id == "INV-0099"


def test_check_duplicate_invoices_different_entity_is_not_a_duplicate():
    invoices = [
        {"invoice_id": "INV-0001", "entity_id": "ENT-001", "invoice_number": "N1", "invoice_type": "AR"},
        {"invoice_id": "INV-0002", "entity_id": "ENT-002", "invoice_number": "N1", "invoice_type": "AR"},
    ]
    assert check_duplicate_invoices(invoices) == []


def test_check_required_fields_passes_a_complete_ar_invoice():
    invoice = {
        "invoice_id": "INV-0001", "invoice_type": "AR", "entity_id": "ENT-001", "customer_id": "CUST-001",
        "invoice_date": "2026-06-01", "currency": "GBP", "amount": 100.0, "status": "open",
    }
    assert check_required_fields(invoice) == []


def test_check_required_fields_flags_missing_entity():
    invoice = {
        "invoice_id": "INV-0001", "invoice_type": "AR", "entity_id": None, "customer_id": "CUST-001",
        "invoice_date": "2026-06-01", "currency": "GBP", "amount": 100.0, "status": "open",
    }
    exceptions = check_required_fields(invoice)
    assert any(e.detail == "required field 'entity_id' is missing" for e in exceptions)


def test_check_required_fields_flags_ar_invoice_missing_customer():
    invoice = {
        "invoice_id": "INV-0001", "invoice_type": "AR", "entity_id": "ENT-001", "customer_id": None,
        "invoice_date": "2026-06-01", "currency": "GBP", "amount": 100.0, "status": "open",
    }
    exceptions = check_required_fields(invoice)
    assert any("AR invoice has no customer_id" in e.detail for e in exceptions)


def test_check_required_fields_flags_ap_invoice_missing_vendor():
    invoice = {
        "invoice_id": "INV-0001", "invoice_type": "AP", "entity_id": "ENT-001", "vendor_id": None,
        "invoice_date": "2026-06-01", "currency": "GBP", "amount": 100.0, "status": "open",
    }
    exceptions = check_required_fields(invoice)
    assert any("AP invoice has no vendor_id" in e.detail for e in exceptions)


def test_check_intercompany_counterpart_matched_pair_has_no_exceptions():
    transactions = [
        {"intercompany_transaction_id": "IC-0001", "reference": "REF-1", "amount": 1000.0},
        {"intercompany_transaction_id": "IC-0002", "reference": "REF-1", "amount": 1000.0},
    ]
    assert check_intercompany_counterpart(transactions) == []


def test_check_intercompany_counterpart_flags_single_sided_reference():
    transactions = [{"intercompany_transaction_id": "IC-0003", "reference": "REF-2", "amount": 1000.0}]
    exceptions = check_intercompany_counterpart(transactions)
    assert len(exceptions) == 1
    assert exceptions[0].rule == "intercompany_no_counterpart"


def test_check_intercompany_counterpart_flags_amount_mismatch():
    transactions = [
        {"intercompany_transaction_id": "IC-0004", "reference": "REF-3", "amount": 1000.0},
        {"intercompany_transaction_id": "IC-0005", "reference": "REF-3", "amount": 900.0},
    ]
    exceptions = check_intercompany_counterpart(transactions)
    assert len(exceptions) == 2
    assert all(e.rule == "intercompany_amount_mismatch" for e in exceptions)
