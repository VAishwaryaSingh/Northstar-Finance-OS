VALID_LINES = [
    {"account_code": "5000", "debit_amount": 100.0},
    {"account_code": "2010", "credit_amount": 100.0},
]


def test_create_balanced_journal_entry_succeeds(client, api_headers, test_entity):
    response = client.post("/journal-entries", json={
        "entity_code": test_entity, "entry_date": "2026-06-05", "period": "2026-06", "currency": "GBP",
        "source": "manual", "classification": "test_entry", "created_by": "USR-001", "approved_by": "USR-004",
        "lines": VALID_LINES,
    }, headers=api_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "posted"
    assert len(body["lines"]) == 2


def test_unbalanced_journal_entry_is_rejected_before_hitting_the_database(client, api_headers, test_entity):
    response = client.post("/journal-entries", json={
        "entity_code": test_entity, "entry_date": "2026-06-05", "period": "2026-06", "currency": "GBP",
        "source": "manual", "classification": "test_entry", "created_by": "USR-001", "approved_by": "USR-004",
        "lines": [{"account_code": "5000", "debit_amount": 100.0}, {"account_code": "2010", "credit_amount": 90.0}],
    }, headers=api_headers)
    assert response.status_code == 422
    assert "not balanced" in response.text


def test_self_approved_journal_entry_is_rejected(client, api_headers, test_entity):
    response = client.post("/journal-entries", json={
        "entity_code": test_entity, "entry_date": "2026-06-05", "period": "2026-06", "currency": "GBP",
        "source": "manual", "classification": "test_entry", "created_by": "USR-001", "approved_by": "USR-001",
        "lines": VALID_LINES,
    }, headers=api_headers)
    assert response.status_code == 422
    assert "maker/checker" in response.text


def test_journal_entry_without_approver_is_pending_approval(client, api_headers, test_entity):
    response = client.post("/journal-entries", json={
        "entity_code": test_entity, "entry_date": "2026-06-05", "period": "2026-06", "currency": "GBP",
        "source": "manual", "classification": "test_entry", "created_by": "USR-001",
        "lines": VALID_LINES,
    }, headers=api_headers)
    assert response.status_code == 201
    assert response.json()["status"] == "pending_approval"
    assert response.json()["approved_by"] is None


def test_journal_entry_with_only_one_line_is_422(client, api_headers, test_entity):
    response = client.post("/journal-entries", json={
        "entity_code": test_entity, "entry_date": "2026-06-05", "period": "2026-06", "currency": "GBP",
        "source": "manual", "classification": "test_entry", "created_by": "USR-001",
        "lines": [{"account_code": "5000", "debit_amount": 100.0}],
    }, headers=api_headers)
    assert response.status_code == 422


def test_journal_line_with_both_debit_and_credit_is_422(client, api_headers, test_entity):
    response = client.post("/journal-entries", json={
        "entity_code": test_entity, "entry_date": "2026-06-05", "period": "2026-06", "currency": "GBP",
        "source": "manual", "classification": "test_entry", "created_by": "USR-001",
        "lines": [
            {"account_code": "5000", "debit_amount": 100.0, "credit_amount": 100.0},
            {"account_code": "2010", "credit_amount": 100.0},
        ],
    }, headers=api_headers)
    assert response.status_code == 422
