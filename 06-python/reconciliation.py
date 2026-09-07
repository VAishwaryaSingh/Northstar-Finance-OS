"""Duplicate detection and transaction matching (Phase 9/13, PLAN.md §21/§26).

05-sql/ap.sql already finds exact-key duplicate invoices with a GROUP BY.
flag_duplicate_invoices does the same detection here, in Python, so it can
sit inside the ingestion pipeline and actually change what gets loaded
(the later duplicate is flagged, not silently treated as a fresh invoice
ready to pay -- this is R10's "flagged before payment, not after").

match_transactions and match_intercompany independently re-derive
bank<->payment and intercompany matches from the raw amounts/dates/
references, rather than trusting the match_status label the source data
already carries -- proving the matching logic actually works, not just
that the synthetic generator's labels can be read back.
"""

from __future__ import annotations

import pandas as pd


def flag_duplicate_invoices(df: pd.DataFrame) -> pd.DataFrame:
    """Mark every row after the first in each (entity_id, invoice_number,
    invoice_type) group as duplicate_flagged. Returns a copy with an added
    'duplicate_of' column (None, or the invoice_id it duplicates)."""
    df = df.copy()
    df["duplicate_of"] = None

    key_cols = ["entity_id", "invoice_number", "invoice_type"]
    for _, group in df.groupby(key_cols, dropna=False):
        if len(group) > 1:
            ordered = group.sort_values("invoice_id")
            keeper_id = ordered.iloc[0]["invoice_id"]
            dup_index = ordered.index[1:]
            df.loc[dup_index, "status"] = "duplicate_flagged"
            df.loc[dup_index, "duplicate_of"] = keeper_id

    return df


def match_transactions(
    bank_df: pd.DataFrame,
    payments_df: pd.DataFrame,
    amount_tolerance: float = 0.01,
    day_tolerance: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Greedily match each bank transaction to an unclaimed payment with the
    same entity and currency, an amount within `amount_tolerance`, and a
    transaction date within `day_tolerance` days of the payment date.

    Returns (matches, unmatched_bank). matches has one row per successful
    match (bank_transaction_id, payment_id); unmatched_bank is the bank
    rows left over.
    """
    bank = bank_df.copy()
    bank["transaction_date"] = pd.to_datetime(bank["transaction_date"])
    payments = payments_df.copy()
    payments["payment_date"] = pd.to_datetime(payments["payment_date"])

    available = payments.copy()
    matches = []
    unmatched_rows = []

    for _, b in bank.iterrows():
        candidates = available[
            (available["entity_id"] == b["entity_id"])
            & (available["currency"] == b["currency"])
            & ((available["amount"] - b["amount"]).abs() <= amount_tolerance)
            & ((available["payment_date"] - b["transaction_date"]).abs() <= pd.Timedelta(days=day_tolerance))
        ]
        if not candidates.empty:
            best = candidates.iloc[0]
            matches.append({
                "bank_transaction_id": b["bank_transaction_id"],
                "payment_id": best["payment_id"],
            })
            available = available.drop(best.name)
        else:
            unmatched_rows.append(b)

    matches_df = pd.DataFrame(matches, columns=["bank_transaction_id", "payment_id"])
    unmatched_df = pd.DataFrame(unmatched_rows) if unmatched_rows else bank.iloc[0:0]
    return matches_df, unmatched_df


def match_intercompany(ic_df: pd.DataFrame, amount_tolerance: float = 0.01) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A reference is 'matched' if both directions (entity_from->entity_to
    and entity_to->entity_from) exist with the same reference and an amount
    within tolerance. Returns (matched, unmatched), split by reference."""
    matched_refs = []
    unmatched_refs = []

    for reference, group in ic_df.groupby("reference"):
        if len(group) < 2:
            unmatched_refs.append(reference)
            continue
        amounts = group["amount"].tolist()
        if max(amounts) - min(amounts) <= amount_tolerance:
            matched_refs.append(reference)
        else:
            unmatched_refs.append(reference)

    matched = ic_df[ic_df["reference"].isin(matched_refs)]
    unmatched = ic_df[ic_df["reference"].isin(unmatched_refs)]
    return matched, unmatched
