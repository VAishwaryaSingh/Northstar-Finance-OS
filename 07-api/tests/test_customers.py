def test_create_customer_succeeds(client, api_headers, test_entity):
    response = client.post("/customers", json={
        "customer_code": "TC001", "customer_name": "Test Customer Ltd",
        "entity_code": test_entity, "billing_currency": "GBP",
    }, headers=api_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["customer_code"] == "TC001"
    assert body["entity_code"] == test_entity
    assert body["status"] == "active"
    assert body["customer_id"].startswith("CUST-")


def test_create_customer_with_unknown_entity_is_404(client, api_headers):
    response = client.post("/customers", json={
        "customer_code": "TC002", "customer_name": "X", "entity_code": "NOPE-00", "billing_currency": "GBP",
    }, headers=api_headers)
    assert response.status_code == 404


def test_create_customer_with_bad_currency_is_422(client, api_headers, test_entity):
    response = client.post("/customers", json={
        "customer_code": "TC003", "customer_name": "X", "entity_code": test_entity, "billing_currency": "EUR",
    }, headers=api_headers)
    assert response.status_code == 422


def test_create_customer_missing_field_is_422(client, api_headers):
    response = client.post("/customers", json={"customer_name": "X"}, headers=api_headers)
    assert response.status_code == 422
