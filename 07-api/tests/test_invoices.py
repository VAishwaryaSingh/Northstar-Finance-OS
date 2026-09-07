import pytest


@pytest.fixture()
def test_customer(client, api_headers, test_entity):
    response = client.post("/customers", json={
        "customer_code": "TC100", "customer_name": "Invoice Test Customer",
        "entity_code": test_entity, "billing_currency": "GBP",
    }, headers=api_headers)
    assert response.status_code == 201
    return response.json()["customer_code"]


def test_create_invoice_succeeds(client, api_headers, test_entity, test_customer):
    response = client.post("/invoices", json={
        "invoice_type": "AR", "invoice_number": "INV-TEST-001", "entity_code": test_entity,
        "customer_code": test_customer, "invoice_date": "2026-06-01", "currency": "GBP",
        "amount": 500.0, "source": "api_test",
    }, headers=api_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "open"
    assert body["idempotent_replay"] is False


def test_ar_invoice_without_customer_code_is_422(client, api_headers, test_entity):
    response = client.post("/invoices", json={
        "invoice_type": "AR", "invoice_number": "INV-TEST-002", "entity_code": test_entity,
        "invoice_date": "2026-06-01", "currency": "GBP", "amount": 500.0, "source": "api_test",
    }, headers=api_headers)
    assert response.status_code == 422


def test_replaying_same_invoice_number_and_amount_is_idempotent(client, api_headers, test_entity, test_customer):
    body_kwargs = {
        "invoice_type": "AR", "invoice_number": "INV-TEST-003", "entity_code": test_entity,
        "customer_code": test_customer, "invoice_date": "2026-06-01", "currency": "GBP",
        "amount": 250.0, "source": "api_test",
    }
    first = client.post("/invoices", json=body_kwargs, headers=api_headers)
    second = client.post("/invoices", json=body_kwargs, headers=api_headers)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["idempotent_replay"] is True
    assert second.json()["invoice_id"] == first.json()["invoice_id"]


def test_replaying_same_invoice_number_different_amount_is_flagged(client, api_headers, test_entity, test_customer):
    first = client.post("/invoices", json={
        "invoice_type": "AR", "invoice_number": "INV-TEST-004", "entity_code": test_entity,
        "customer_code": test_customer, "invoice_date": "2026-06-01", "currency": "GBP",
        "amount": 250.0, "source": "api_test",
    }, headers=api_headers)
    second = client.post("/invoices", json={
        "invoice_type": "AR", "invoice_number": "INV-TEST-004", "entity_code": test_entity,
        "customer_code": test_customer, "invoice_date": "2026-06-01", "currency": "GBP",
        "amount": 999.0, "source": "api_test",
    }, headers=api_headers)

    assert first.status_code == 201
    assert second.status_code == 201  # a new row really was created
    assert second.json()["idempotent_replay"] is False
    assert second.json()["status"] == "duplicate_flagged"
    assert second.json()["invoice_id"] != first.json()["invoice_id"]


def test_create_invoice_with_unknown_customer_is_404(client, api_headers, test_entity):
    response = client.post("/invoices", json={
        "invoice_type": "AR", "invoice_number": "INV-TEST-005", "entity_code": test_entity,
        "customer_code": "NOPE-00", "invoice_date": "2026-06-01", "currency": "GBP",
        "amount": 500.0, "source": "api_test",
    }, headers=api_headers)
    assert response.status_code == 404
