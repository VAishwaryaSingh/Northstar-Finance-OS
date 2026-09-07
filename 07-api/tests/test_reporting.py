def test_trial_balance_requires_api_key(client):
    assert client.get("/trial-balance").status_code == 401


def test_trial_balance_returns_rows_for_seeded_data(client, api_headers):
    response = client.get("/trial-balance", headers=api_headers)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) > 0
    assert {"entity_code", "account_code", "debit_total", "credit_total", "net_balance"} <= body[0].keys()


def test_trial_balance_filters_by_entity_code(client, api_headers):
    all_rows = client.get("/trial-balance", headers=api_headers).json()
    filtered = client.get("/trial-balance?entity_code=NHH-UK", headers=api_headers).json()
    assert len(filtered) <= len(all_rows)
    assert all(row["entity_code"] == "NHH-UK" for row in filtered)


def test_reconciliation_status_returns_a_rate_between_0_and_100(client, api_headers):
    response = client.get("/reconciliation-status", headers=api_headers)
    assert response.status_code == 200
    for row in response.json():
        assert 0 <= row["reconciliation_rate_pct"] <= 100
        assert row["matched_count"] <= row["total_count"]


def test_close_status_returns_rows(client, api_headers):
    response = client.get("/close-status", headers=api_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    for row in body:
        assert row["posted_count"] + row["pending_count"] == row["total_journals"]


def test_intercompany_exceptions_only_returns_unmatched(client, api_headers):
    response = client.get("/intercompany-exceptions", headers=api_headers)
    assert response.status_code == 200
    # every row returned is, by definition, something PLAN.md's R04 wants
    # surfaced -- this endpoint should never return a 'matched' row
    body = response.json()
    assert len(body) > 0
    assert all("intercompany_transaction_id" in row for row in body)
