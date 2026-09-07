"""Metric computation for the Close Control Centre (Phase 14, PLAN.md §27).

Every function here takes an open SQLAlchemy connection and returns a
plain pandas DataFrame or dict -- no Streamlit imports in this file, so
every metric is independently testable and runnable from a plain Python
REPL, per PLAN.md §27's requirement that "the repository should retain
reproducible data and queries" regardless of which dashboard tool
(Streamlit here, Power BI would also be acceptable) renders them.

Most metrics are plain SQL, matching the equivalent queries already
proven in 05-sql/ and 07-api/models.py. Two categories -- data-quality
exceptions and AI-recommendations-awaiting-review -- call directly into
08-accounting-automation's actual rule functions instead of
reimplementing them a third time: those are genuine rule logic, not
aggregation, and this dashboard should show what the rules that actually
run elsewhere in this project actually find, not a fourth opinion.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Connection

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "08-accounting-automation"))

from exception_rules import (  # noqa: E402
    check_duplicate_invoices,
    check_intercompany_counterpart,
    check_required_fields,
)
from invoice_classification import classify_vendor_account  # noqa: E402

# Standing in for "today" in this fictional project's timeline -- same
# reference date already used in 05-sql/ap.sql, kept consistent here.
REFERENCE_DATE = date(2026, 9, 7)


def get_close_progress(conn: Connection) -> pd.DataFrame:
    """Per entity/period: how much of the close is actually posted."""
    query = """
        SELECT e.entity_code, je.period,
               COUNT(*) AS total_journals,
               COUNT(*) FILTER (WHERE je.status = 'posted') AS posted_count,
               ROUND(100.0 * COUNT(*) FILTER (WHERE je.status = 'posted') / NULLIF(COUNT(*), 0), 1) AS close_complete_pct
        FROM journal_entries je JOIN entities e ON e.entity_id = je.entity_id
        GROUP BY e.entity_code, je.period
        ORDER BY e.entity_code, je.period
    """
    return pd.read_sql(text(query), conn)


def get_outstanding_reconciliations(conn: Connection) -> dict:
    """Count of not-yet-matched items, bank and intercompany combined --
    same 'outstanding' concept close_progress uses for journals, applied
    to the two reconciliation areas with a live match_status column."""
    bank_unmatched = conn.execute(text(
        "SELECT COUNT(*) FROM bank_transactions WHERE match_status <> 'matched'"
    )).scalar()
    ic_unmatched = conn.execute(text(
        "SELECT COUNT(*) FROM intercompany_transactions WHERE match_status <> 'matched'"
    )).scalar()
    return {"bank_outstanding": bank_unmatched, "intercompany_outstanding": ic_unmatched}


def get_unreconciled_cash(conn: Connection) -> pd.DataFrame:
    """Not just a count -- the actual amount sitting unreconciled, by
    entity and currency, since that's what a CFO actually cares about."""
    query = """
        SELECT e.entity_code, b.currency,
               COUNT(*) AS transaction_count,
               SUM(b.amount) AS unreconciled_amount
        FROM bank_transactions b JOIN entities e ON e.entity_id = b.entity_id
        WHERE b.match_status <> 'matched'
        GROUP BY e.entity_code, b.currency
        ORDER BY e.entity_code, b.currency
    """
    return pd.read_sql(text(query), conn)


def get_unapproved_journals(conn: Connection) -> pd.DataFrame:
    query = """
        SELECT je.journal_entry_id, e.entity_code, je.period, je.classification,
               je.created_by, je.status,
               COALESCE(SUM(jl.debit_amount), 0) AS amount
        FROM journal_entries je
        JOIN entities e ON e.entity_id = je.entity_id
        JOIN journal_lines jl ON jl.journal_entry_id = je.journal_entry_id
        WHERE je.status <> 'posted'
        GROUP BY je.journal_entry_id, e.entity_code, je.period, je.classification, je.created_by, je.status
        ORDER BY amount DESC
    """
    return pd.read_sql(text(query), conn)


def get_intercompany_exceptions(conn: Connection) -> pd.DataFrame:
    query = """
        SELECT ic.intercompany_transaction_id, ef.entity_code AS entity_from_code,
               et.entity_code AS entity_to_code, ic.transaction_date, ic.currency,
               ic.amount, ic.reference, ic.match_status
        FROM intercompany_transactions ic
        JOIN entities ef ON ef.entity_id = ic.entity_from_id
        JOIN entities et ON et.entity_id = ic.entity_to_id
        WHERE ic.match_status <> 'matched'
        ORDER BY ic.transaction_date
    """
    return pd.read_sql(text(query), conn)


def get_overdue_ap(conn: Connection, reference_date: date = REFERENCE_DATE) -> pd.DataFrame:
    query = """
        SELECT i.invoice_id, e.entity_code, v.vendor_name, i.due_date,
               (:ref_date - i.due_date) AS days_overdue, i.currency, i.amount
        FROM invoices i
        JOIN entities e ON e.entity_id = i.entity_id
        LEFT JOIN vendors v ON v.vendor_id = i.vendor_id
        LEFT JOIN payments p ON p.invoice_id = i.invoice_id
        WHERE i.invoice_type = 'AP' AND p.payment_id IS NULL AND i.due_date < :ref_date
        ORDER BY days_overdue DESC
    """
    return pd.read_sql(text(query), conn, params={"ref_date": reference_date})


def get_manual_journal_pct(conn: Connection) -> dict:
    query = """
        SELECT source, COUNT(*) AS journal_count
        FROM journal_entries
        GROUP BY source
    """
    df = pd.read_sql(text(query), conn)
    total = int(df["journal_count"].sum())
    manual = int(df.loc[df["source"] == "manual", "journal_count"].sum()) if "manual" in df["source"].values else 0
    return {
        "manual_count": manual,
        "total_count": total,
        "manual_pct": round(100.0 * manual / total, 1) if total else 0.0,
    }


def get_ai_recommendations_awaiting_review(conn: Connection) -> pd.DataFrame:
    """Live-runs 08-accounting-automation's actual vendor->account rule
    against every AP invoice -- an account mismatch is exactly the kind
    of ambiguous case Phase 12's AI assistant exists to help a human
    review (see 09-ai/accounting_agent.py), so this is what's really
    waiting for that review right now, not a snapshot of a past run."""
    invoices = pd.read_sql(text("""
        SELECT i.invoice_id, e.entity_code, v.vendor_name, i.account_id, v.default_account_id,
               a.account_code AS invoice_account_code, d.account_code AS vendor_default_account_code,
               i.amount, i.currency
        FROM invoices i
        JOIN entities e ON e.entity_id = i.entity_id
        LEFT JOIN vendors v ON v.vendor_id = i.vendor_id
        LEFT JOIN chart_of_accounts a ON a.account_id = i.account_id
        LEFT JOIN chart_of_accounts d ON d.account_id = v.default_account_id
        WHERE i.invoice_type = 'AP'
    """), conn)

    rows = []
    for _, inv in invoices.iterrows():
        result = classify_vendor_account(inv["default_account_id"], inv["account_id"])
        if result.exception:
            rows.append({
                "invoice_id": inv["invoice_id"], "entity_code": inv["entity_code"],
                "vendor_name": inv["vendor_name"], "amount": inv["amount"], "currency": inv["currency"],
                "invoice_account_code": inv["invoice_account_code"],
                "vendor_default_account_code": inv["vendor_default_account_code"],
                "reason": result.exception,
            })
    return pd.DataFrame(rows)


def get_data_quality_exceptions(conn: Connection) -> pd.DataFrame:
    """Live-runs three of 08-accounting-automation's exception rules
    against the current database state."""
    invoices = pd.read_sql(text("""
        SELECT invoice_id, entity_id, invoice_number, invoice_type, customer_id, vendor_id,
               invoice_date, currency, amount, status
        FROM invoices
    """), conn).to_dict(orient="records")
    intercompany = pd.read_sql(text("""
        SELECT intercompany_transaction_id, reference, amount FROM intercompany_transactions
    """), conn).to_dict(orient="records")

    findings = []
    findings += check_duplicate_invoices(invoices)
    for inv in invoices:
        findings += check_required_fields(inv)
    findings += check_intercompany_counterpart(intercompany)

    return pd.DataFrame([{"rule": f.rule, "id": f.id, "detail": f.detail} for f in findings])


def get_all_metrics(conn: Connection) -> dict:
    """Bundles every metric for a single dashboard render pass."""
    return {
        "close_progress": get_close_progress(conn),
        "outstanding_reconciliations": get_outstanding_reconciliations(conn),
        "unreconciled_cash": get_unreconciled_cash(conn),
        "unapproved_journals": get_unapproved_journals(conn),
        "intercompany_exceptions": get_intercompany_exceptions(conn),
        "overdue_ap": get_overdue_ap(conn),
        "manual_journal_pct": get_manual_journal_pct(conn),
        "ai_recommendations_awaiting_review": get_ai_recommendations_awaiting_review(conn),
        "data_quality_exceptions": get_data_quality_exceptions(conn),
    }
