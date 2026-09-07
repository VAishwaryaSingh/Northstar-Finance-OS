def test_create_payment_without_invoice_succeeds(client, api_headers, test_entity):
    # unapplied cash receipt -- invoice_id is optional (see data-model.md)
    response = client.post("/payments", json={
        "entity_code": test_entity, "payment_date": "2026-06-05", "currency": "GBP",
        "amount": 1000.0, "payment_type": "received", "source": "api_test",
    }, headers=api_headers)
    assert response.status_code == 201
    assert response.json()["invoice_id"] is None


def test_create_payment_with_unknown_invoice_is_404(client, api_headers, test_entity):
    response = client.post("/payments", json={
        "entity_code": test_entity, "invoice_id": "INV-DOES-NOT-EXIST", "payment_date": "2026-06-05",
        "currency": "GBP", "amount": 1000.0, "payment_type": "received", "source": "api_test",
    }, headers=api_headers)
    assert response.status_code == 404


def test_create_payment_with_negative_amount_is_422(client, api_headers, test_entity):
    response = client.post("/payments", json={
        "entity_code": test_entity, "payment_date": "2026-06-05", "currency": "GBP",
        "amount": -50.0, "payment_type": "received", "source": "api_test",
    }, headers=api_headers)
    assert response.status_code == 422
