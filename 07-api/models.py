"""Data access layer -- parameterized SQL against the schema from
03-architecture/data-model.md / 05-sql/schema.sql, using SQLAlchemy Core
rather than an ORM. A hand-written schema.sql with deferred triggers and
CHECK constraints doesn't map cleanly onto ORM relationships, and plain
SQL keeps this readable without adding a second layer of abstraction on
top of SQL the rest of the project already uses directly.

Every function takes an open `conn` (a SQLAlchemy Connection, usually
inside a transaction the caller controls) so a route can compose several
of these into one atomic unit of work.
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Connection

from errors import NotFoundError


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


# ---------------------------------------------------------------------------
# Code -> ID resolution (mirrors 06-python/mappings.py's exact-match half;
# the API doesn't do fuzzy vendor matching -- an API caller is expected to
# send a code that already exists, unlike a messy source file)
# ---------------------------------------------------------------------------

def resolve_entity_id(conn: Connection, entity_code: str) -> str:
    row = conn.execute(text("SELECT entity_id FROM entities WHERE entity_code = :c"), {"c": entity_code}).first()
    if row is None:
        raise NotFoundError(f"unknown entity_code {entity_code!r}")
    return row[0]


def resolve_customer_id(conn: Connection, customer_code: str) -> str:
    row = conn.execute(text("SELECT customer_id FROM customers WHERE customer_code = :c"), {"c": customer_code}).first()
    if row is None:
        raise NotFoundError(f"unknown customer_code {customer_code!r}")
    return row[0]


def resolve_vendor_id(conn: Connection, vendor_code: str) -> str:
    row = conn.execute(text("SELECT vendor_id FROM vendors WHERE vendor_code = :c"), {"c": vendor_code}).first()
    if row is None:
        raise NotFoundError(f"unknown vendor_code {vendor_code!r}")
    return row[0]


def resolve_account_id(conn: Connection, account_code: Optional[str]) -> Optional[str]:
    if account_code is None:
        return None
    row = conn.execute(text("SELECT account_id FROM chart_of_accounts WHERE account_code = :c"), {"c": account_code}).first()
    if row is None:
        raise NotFoundError(f"unknown account_code {account_code!r}")
    return row[0]


def resolve_user_id(conn: Connection, user_id_or_code: str) -> str:
    row = conn.execute(text("SELECT user_id FROM users WHERE user_id = :u"), {"u": user_id_or_code}).first()
    if row is None:
        raise NotFoundError(f"unknown user_id {user_id_or_code!r}")
    return row[0]


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

def create_customer(conn: Connection, data) -> dict:
    entity_id = resolve_entity_id(conn, data.entity_code)
    customer_id = new_id("CUST")
    conn.execute(
        text("""
            INSERT INTO customers (customer_id, customer_code, customer_name, entity_id, billing_currency, status)
            VALUES (:customer_id, :customer_code, :customer_name, :entity_id, :billing_currency, 'active')
        """),
        {
            "customer_id": customer_id,
            "customer_code": data.customer_code,
            "customer_name": data.customer_name,
            "entity_id": entity_id,
            "billing_currency": data.billing_currency,
        },
    )
    return get_customer_by_id(conn, customer_id)


def get_customer_by_id(conn: Connection, customer_id: str) -> dict:
    row = conn.execute(
        text("""
            SELECT c.customer_id, c.customer_code, c.customer_name, e.entity_code, c.billing_currency, c.status
            FROM customers c JOIN entities e ON e.entity_id = c.entity_id
            WHERE c.customer_id = :id
        """),
        {"id": customer_id},
    ).mappings().first()
    if row is None:
        raise NotFoundError(f"customer {customer_id!r} not found")
    return dict(row)


# ---------------------------------------------------------------------------
# Invoices -- POST /invoices is idempotent on (entity_code, invoice_number,
# invoice_type): a replay with the same amount returns the existing row
# rather than creating a duplicate; a replay with a different amount is
# inserted but flagged, the same way 06-python/reconciliation.py flags
# duplicates found in a source file (R10).
# ---------------------------------------------------------------------------

def create_invoice(conn: Connection, data) -> tuple[dict, bool]:
    entity_id = resolve_entity_id(conn, data.entity_code)
    customer_id = resolve_customer_id(conn, data.customer_code) if data.customer_code else None
    vendor_id = resolve_vendor_id(conn, data.vendor_code) if data.vendor_code else None
    account_id = resolve_account_id(conn, data.account_code)

    existing = conn.execute(
        text("""
            SELECT invoice_id, amount FROM invoices
            WHERE entity_id = :entity_id AND invoice_number = :invoice_number AND invoice_type = :invoice_type
        """),
        {"entity_id": entity_id, "invoice_number": data.invoice_number, "invoice_type": data.invoice_type},
    ).first()

    if existing is not None:
        existing_id, existing_amount = existing
        if round(float(existing_amount), 2) == round(data.amount, 2):
            return get_invoice_by_id(conn, existing_id), True
        status_value = "duplicate_flagged"
    else:
        status_value = "open"

    invoice_id = new_id("INV")
    conn.execute(
        text("""
            INSERT INTO invoices (invoice_id, invoice_type, invoice_number, entity_id, customer_id, vendor_id,
                                   invoice_date, due_date, currency, amount, source, account_id, status)
            VALUES (:invoice_id, :invoice_type, :invoice_number, :entity_id, :customer_id, :vendor_id,
                    :invoice_date, :due_date, :currency, :amount, :source, :account_id, :status)
        """),
        {
            "invoice_id": invoice_id, "invoice_type": data.invoice_type, "invoice_number": data.invoice_number,
            "entity_id": entity_id, "customer_id": customer_id, "vendor_id": vendor_id,
            "invoice_date": data.invoice_date, "due_date": data.due_date, "currency": data.currency,
            "amount": data.amount, "source": data.source, "account_id": account_id, "status": status_value,
        },
    )
    return get_invoice_by_id(conn, invoice_id), False


def get_invoice_by_id(conn: Connection, invoice_id: str) -> dict:
    row = conn.execute(
        text("""
            SELECT i.invoice_id, i.invoice_type, i.invoice_number, e.entity_code,
                   c.customer_code, v.vendor_code, i.invoice_date, i.due_date,
                   i.currency, i.amount, i.source, a.account_code, i.status
            FROM invoices i
            JOIN entities e ON e.entity_id = i.entity_id
            LEFT JOIN customers c ON c.customer_id = i.customer_id
            LEFT JOIN vendors v ON v.vendor_id = i.vendor_id
            LEFT JOIN chart_of_accounts a ON a.account_id = i.account_id
            WHERE i.invoice_id = :id
        """),
        {"id": invoice_id},
    ).mappings().first()
    if row is None:
        raise NotFoundError(f"invoice {invoice_id!r} not found")
    return dict(row)


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

def create_payment(conn: Connection, data) -> dict:
    entity_id = resolve_entity_id(conn, data.entity_code)
    invoice_id = None
    if data.invoice_id is not None:
        get_invoice_by_id(conn, data.invoice_id)  # raises NotFoundError if missing
        invoice_id = data.invoice_id

    payment_id = new_id("PAY")
    conn.execute(
        text("""
            INSERT INTO payments (payment_id, entity_id, invoice_id, payment_date, currency, amount,
                                   payment_type, source, status)
            VALUES (:payment_id, :entity_id, :invoice_id, :payment_date, :currency, :amount,
                    :payment_type, :source, 'pending')
        """),
        {
            "payment_id": payment_id, "entity_id": entity_id, "invoice_id": invoice_id,
            "payment_date": data.payment_date, "currency": data.currency, "amount": data.amount,
            "payment_type": data.payment_type, "source": data.source,
        },
    )
    return get_payment_by_id(conn, payment_id)


def get_payment_by_id(conn: Connection, payment_id: str) -> dict:
    row = conn.execute(
        text("""
            SELECT p.payment_id, e.entity_code, p.invoice_id, p.payment_date, p.currency,
                   p.amount, p.payment_type, p.source, p.status
            FROM payments p JOIN entities e ON e.entity_id = p.entity_id
            WHERE p.payment_id = :id
        """),
        {"id": payment_id},
    ).mappings().first()
    if row is None:
        raise NotFoundError(f"payment {payment_id!r} not found")
    return dict(row)


# ---------------------------------------------------------------------------
# Journal entries -- inserted as a single unit (header + lines) inside the
# caller's transaction, so schema.sql's deferred balance trigger validates
# them together at commit, exactly as seed.sql relies on (see its header
# comment on the trigger).
# ---------------------------------------------------------------------------

def create_journal_entry(conn: Connection, data) -> dict:
    entity_id = resolve_entity_id(conn, data.entity_code)
    created_by = resolve_user_id(conn, data.created_by)
    approved_by = resolve_user_id(conn, data.approved_by) if data.approved_by else None
    status_value = "posted" if approved_by else "pending_approval"

    journal_entry_id = new_id("JE")
    conn.execute(
        text("""
            INSERT INTO journal_entries (journal_entry_id, entity_id, entry_date, period, currency,
                                          source, classification, status, created_by, approved_by, description)
            VALUES (:id, :entity_id, :entry_date, :period, :currency, :source, :classification,
                    :status, :created_by, :approved_by, :description)
        """),
        {
            "id": journal_entry_id, "entity_id": entity_id, "entry_date": data.entry_date, "period": data.period,
            "currency": data.currency, "source": data.source, "classification": data.classification,
            "status": status_value, "created_by": created_by, "approved_by": approved_by,
            "description": data.description,
        },
    )

    for line in data.lines:
        account_id = resolve_account_id(conn, line.account_code)
        conn.execute(
            text("""
                INSERT INTO journal_lines (journal_line_id, journal_entry_id, account_id, debit_amount,
                                            credit_amount, line_description)
                VALUES (:id, :journal_entry_id, :account_id, :debit_amount, :credit_amount, :line_description)
            """),
            {
                "id": new_id("JL"), "journal_entry_id": journal_entry_id, "account_id": account_id,
                "debit_amount": line.debit_amount, "credit_amount": line.credit_amount,
                "line_description": line.line_description,
            },
        )

    return get_journal_entry_by_id(conn, journal_entry_id)


def get_journal_entry_by_id(conn: Connection, journal_entry_id: str) -> dict:
    header = conn.execute(
        text("""
            SELECT je.journal_entry_id, e.entity_code, je.entry_date, je.period, je.currency,
                   je.source, je.classification, je.status, je.created_by, je.approved_by, je.description
            FROM journal_entries je JOIN entities e ON e.entity_id = je.entity_id
            WHERE je.journal_entry_id = :id
        """),
        {"id": journal_entry_id},
    ).mappings().first()
    if header is None:
        raise NotFoundError(f"journal entry {journal_entry_id!r} not found")

    lines = conn.execute(
        text("""
            SELECT jl.journal_line_id, a.account_code, jl.debit_amount, jl.credit_amount, jl.line_description
            FROM journal_lines jl JOIN chart_of_accounts a ON a.account_id = jl.account_id
            WHERE jl.journal_entry_id = :id
            ORDER BY jl.journal_line_id
        """),
        {"id": journal_entry_id},
    ).mappings().all()

    result = dict(header)
    result["lines"] = [dict(line) for line in lines]
    return result


# ---------------------------------------------------------------------------
# Reporting (GET endpoints) -- same logic as 05-sql/reporting.sql,
# reconciliation.sql, close_analysis.sql, and intercompany.sql, exposed
# over HTTP with optional entity_code/period filters.
# ---------------------------------------------------------------------------

def get_trial_balance(conn: Connection, entity_code: Optional[str] = None) -> list[dict]:
    query = """
        SELECT e.entity_code, a.account_code, a.account_name, a.account_type,
               COALESCE(SUM(jl.debit_amount), 0) AS debit_total,
               COALESCE(SUM(jl.credit_amount), 0) AS credit_total,
               COALESCE(SUM(jl.debit_amount) - SUM(jl.credit_amount), 0) AS net_balance
        FROM journal_lines jl
        JOIN journal_entries je ON je.journal_entry_id = jl.journal_entry_id
        JOIN entities e ON e.entity_id = je.entity_id
        JOIN chart_of_accounts a ON a.account_id = jl.account_id
        WHERE je.status = 'posted'
    """
    params: dict = {}
    if entity_code:
        query += " AND e.entity_code = :entity_code"
        params["entity_code"] = entity_code
    query += " GROUP BY e.entity_code, a.account_code, a.account_name, a.account_type ORDER BY e.entity_code, a.account_code"
    return [dict(row) for row in conn.execute(text(query), params).mappings().all()]


def get_reconciliation_status(conn: Connection, entity_code: Optional[str] = None) -> list[dict]:
    query = """
        SELECT e.entity_code,
               COUNT(*) FILTER (WHERE b.match_status = 'matched') AS matched_count,
               COUNT(*) AS total_count,
               ROUND(100.0 * COUNT(*) FILTER (WHERE b.match_status = 'matched') / NULLIF(COUNT(*), 0), 1) AS reconciliation_rate_pct
        FROM bank_transactions b JOIN entities e ON e.entity_id = b.entity_id
    """
    params: dict = {}
    if entity_code:
        query += " WHERE e.entity_code = :entity_code"
        params["entity_code"] = entity_code
    query += " GROUP BY e.entity_code ORDER BY e.entity_code"
    return [dict(row) for row in conn.execute(text(query), params).mappings().all()]


def get_close_status(conn: Connection, entity_code: Optional[str] = None, period: Optional[str] = None) -> list[dict]:
    query = """
        SELECT e.entity_code, je.period,
               COUNT(*) AS total_journals,
               COUNT(*) FILTER (WHERE je.status = 'posted') AS posted_count,
               COUNT(*) FILTER (WHERE je.status <> 'posted') AS pending_count,
               ROUND(100.0 * COUNT(*) FILTER (WHERE je.status = 'posted') / NULLIF(COUNT(*), 0), 1) AS close_complete_pct
        FROM journal_entries je JOIN entities e ON e.entity_id = je.entity_id
        WHERE 1 = 1
    """
    params: dict = {}
    if entity_code:
        query += " AND e.entity_code = :entity_code"
        params["entity_code"] = entity_code
    if period:
        query += " AND je.period = :period"
        params["period"] = period
    query += " GROUP BY e.entity_code, je.period ORDER BY e.entity_code, je.period"
    return [dict(row) for row in conn.execute(text(query), params).mappings().all()]


def get_intercompany_exceptions(conn: Connection, entity_code: Optional[str] = None) -> list[dict]:
    query = """
        SELECT ic.intercompany_transaction_id, ef.entity_code AS entity_from_code,
               et.entity_code AS entity_to_code, ic.transaction_date, ic.currency, ic.amount, ic.reference
        FROM intercompany_transactions ic
        JOIN entities ef ON ef.entity_id = ic.entity_from_id
        JOIN entities et ON et.entity_id = ic.entity_to_id
        WHERE ic.match_status <> 'matched'
    """
    params: dict = {}
    if entity_code:
        query += " AND (ef.entity_code = :entity_code OR et.entity_code = :entity_code)"
        params["entity_code"] = entity_code
    query += " ORDER BY ic.transaction_date"
    return [dict(row) for row in conn.execute(text(query), params).mappings().all()]
