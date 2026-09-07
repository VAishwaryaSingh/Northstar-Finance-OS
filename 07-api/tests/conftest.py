"""Test fixtures for the API test suite.

Tests run against the real local `northstar` PostgreSQL database (same
approach as 06-python's tests being run manually against it) rather than a
mock -- but each test gets its own throwaway entity_code so it can create
real customers/invoices/journal entries through the actual API without
touching the Phase 7/8/9 seeded data. test_entity's teardown deletes
everything created under that entity_code, in FK-safe order.
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from config import API_SECRET_KEY
from db import get_engine
from main import app


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def api_headers():
    return {"X-API-Key": API_SECRET_KEY}


@pytest.fixture()
def test_entity():
    """Creates a throwaway entity for one test, and deletes everything
    created under it (in FK-safe order) afterwards."""
    engine = get_engine()
    entity_code = f"TST-{uuid.uuid4().hex[:6].upper()}"
    entity_id = f"ENT-{uuid.uuid4().hex[:8].upper()}"

    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO entities (entity_id, entity_code, entity_name, country, functional_currency, status)
                VALUES (:id, :code, 'API Test Entity', 'Testland', 'GBP', 'active')
            """),
            {"id": entity_id, "code": entity_code},
        )

    yield entity_code

    with engine.begin() as conn:
        conn.execute(text("""
            DELETE FROM journal_lines WHERE journal_entry_id IN (
                SELECT journal_entry_id FROM journal_entries WHERE entity_id = :id
            )
        """), {"id": entity_id})
        conn.execute(text("DELETE FROM journal_entries WHERE entity_id = :id"), {"id": entity_id})
        conn.execute(text("DELETE FROM payments WHERE entity_id = :id"), {"id": entity_id})
        conn.execute(text("DELETE FROM invoices WHERE entity_id = :id"), {"id": entity_id})
        conn.execute(text("DELETE FROM customers WHERE entity_id = :id"), {"id": entity_id})
        conn.execute(text("DELETE FROM entities WHERE entity_id = :id"), {"id": entity_id})
