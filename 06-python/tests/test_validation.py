import pandas as pd
from validation import InvoiceRow, validate_rows


def test_valid_invoice_row_passes():
    df = pd.DataFrame([{
        "invoice_id": "INV-0001", "invoice_type": "AR", "invoice_number": "NHH-AR-1",
        "entity_code": "NHH-UK", "customer_code": "C0001", "vendor_code": None,
        "vendor_name_raw": None, "invoice_date": "2026-06-05", "due_date": "2026-07-05",
        "currency": "GBP", "amount": 1000.0, "source": "billing_api",
        "account_code": "4000", "status": "open",
    }])
    valid, errors = validate_rows(df, InvoiceRow)
    assert len(valid) == 1
    assert errors == []


def test_invalid_currency_is_rejected():
    df = pd.DataFrame([{
        "invoice_id": "INV-0001", "invoice_type": "AR", "invoice_number": "NHH-AR-1",
        "entity_code": "NHH-UK", "customer_code": "C0001", "vendor_code": None,
        "vendor_name_raw": None, "invoice_date": "2026-06-05", "due_date": "2026-07-05",
        "currency": "EUR", "amount": 1000.0, "source": "billing_api",
        "account_code": "4000", "status": "open",
    }])
    valid, errors = validate_rows(df, InvoiceRow)
    assert valid == []
    assert len(errors) == 1
    assert errors[0]["id_hint"] == "INV-0001"


def test_negative_amount_is_rejected():
    df = pd.DataFrame([{
        "invoice_id": "INV-0001", "invoice_type": "AR", "invoice_number": "NHH-AR-1",
        "entity_code": "NHH-UK", "customer_code": "C0001", "vendor_code": None,
        "vendor_name_raw": None, "invoice_date": "2026-06-05", "due_date": "2026-07-05",
        "currency": "GBP", "amount": -50.0, "source": "billing_api",
        "account_code": "4000", "status": "open",
    }])
    valid, errors = validate_rows(df, InvoiceRow)
    assert valid == []
    assert len(errors) == 1


def test_invalid_invoice_type_is_rejected():
    df = pd.DataFrame([{
        "invoice_id": "INV-0001", "invoice_type": "XX", "invoice_number": "NHH-AR-1",
        "entity_code": "NHH-UK", "customer_code": "C0001", "vendor_code": None,
        "vendor_name_raw": None, "invoice_date": "2026-06-05", "due_date": "2026-07-05",
        "currency": "GBP", "amount": 1000.0, "source": "billing_api",
        "account_code": "4000", "status": "open",
    }])
    valid, errors = validate_rows(df, InvoiceRow)
    assert valid == []
    assert len(errors) == 1


def test_blank_entity_code_passes_schema_validation():
    # A missing entity_code is a data-quality/mapping problem, not a
    # structural one -- schema validation should not reject it; mapping.py
    # is where this becomes an exception (see ingestion.py).
    df = pd.DataFrame([{
        "invoice_id": "INV-0001", "invoice_type": "AR", "invoice_number": "NHH-AR-1",
        "entity_code": None, "customer_code": "C0001", "vendor_code": None,
        "vendor_name_raw": None, "invoice_date": "2026-06-05", "due_date": "2026-07-05",
        "currency": "GBP", "amount": 1000.0, "source": "billing_api",
        "account_code": "4000", "status": "open",
    }])
    valid, errors = validate_rows(df, InvoiceRow)
    assert len(valid) == 1
    assert errors == []
