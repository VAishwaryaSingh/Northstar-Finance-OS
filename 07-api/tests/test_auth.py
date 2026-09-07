def test_missing_api_key_is_rejected(client):
    response = client.post("/customers", json={
        "customer_code": "C0000", "customer_name": "X", "entity_code": "NHH-UK", "billing_currency": "GBP",
    })
    assert response.status_code == 401


def test_wrong_api_key_is_rejected(client):
    response = client.post(
        "/customers",
        json={"customer_code": "C0000", "customer_name": "X", "entity_code": "NHH-UK", "billing_currency": "GBP"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


def test_health_check_needs_no_api_key(client):
    # /health is deliberately not behind auth -- an unauthenticated
    # liveness check is normal (a load balancer shouldn't need a key).
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
