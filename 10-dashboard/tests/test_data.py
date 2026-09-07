"""Tests run against the real northstar database (read-only queries only,
nothing here writes) -- same approach as 07-api's and 09-ai's DB-touching
tests elsewhere in this project."""

import pytest
from db import get_engine

import data


@pytest.fixture(scope="module")
def conn():
    engine = get_engine()
    with engine.connect() as connection:
        yield connection


def test_close_progress_returns_rows_with_valid_percentages(conn):
    df = data.get_close_progress(conn)
    assert len(df) > 0
    assert (df["close_complete_pct"].dropna() <= 100).all()
    assert (df["close_complete_pct"].dropna() >= 0).all()


def test_outstanding_reconciliations_returns_non_negative_counts(conn):
    result = data.get_outstanding_reconciliations(conn)
    assert result["bank_outstanding"] >= 0
    assert result["intercompany_outstanding"] >= 0


def test_unreconciled_cash_only_includes_non_matched_rows(conn):
    df = data.get_unreconciled_cash(conn)
    # every row represents at least one unmatched/probable_match transaction
    assert (df["transaction_count"] > 0).all()


def test_unapproved_journals_never_includes_posted_status(conn):
    df = data.get_unapproved_journals(conn)
    assert (df["status"] != "posted").all()


def test_intercompany_exceptions_never_includes_matched_status(conn):
    df = data.get_intercompany_exceptions(conn)
    assert (df["match_status"] != "matched").all()


def test_overdue_ap_all_rows_are_actually_overdue(conn):
    df = data.get_overdue_ap(conn)
    assert (df["days_overdue"] > 0).all()


def test_manual_journal_pct_is_a_valid_percentage(conn):
    result = data.get_manual_journal_pct(conn)
    assert 0 <= result["manual_pct"] <= 100
    assert result["manual_count"] <= result["total_count"]


def test_ai_recommendations_awaiting_review_matches_known_count(conn):
    # Cross-check against 08-accounting-automation/rule-findings.md's
    # "Incorrect Account Mapping" count -- this function runs the exact
    # same rule live, so it should agree.
    df = data.get_ai_recommendations_awaiting_review(conn)
    assert len(df) == 4


def test_data_quality_exceptions_has_no_false_missing_field_hits(conn):
    # Regression test: get_data_quality_exceptions originally queried
    # invoices without selecting invoice_date/currency/amount, so every
    # single invoice came back as "missing" those fields (264 false
    # positives against 88 real invoices). None of the real, fully-loaded
    # invoices in this database are actually missing a required field --
    # see 06-python/README.md's discussion of why (they were excluded at
    # load time if they were), so this rule should find nothing here.
    df = data.get_data_quality_exceptions(conn)
    missing_field_rows = df[df["rule"] == "missing_required_field"]
    assert len(missing_field_rows) == 0


def test_get_all_metrics_returns_every_key(conn):
    metrics = data.get_all_metrics(conn)
    expected_keys = {
        "close_progress", "outstanding_reconciliations", "unreconciled_cash",
        "unapproved_journals", "intercompany_exceptions", "overdue_ap",
        "manual_journal_pct", "ai_recommendations_awaiting_review", "data_quality_exceptions",
    }
    assert set(metrics.keys()) == expected_keys
