"""Reconciliation Engine (Phase 13, PLAN.md §26).

reconciliation.py's match_transactions/match_intercompany (Phase 9) are
binary: matched or not, built to drive what the ingestion pipeline loads.
This module is the dedicated, deeper engine PLAN.md §26 asks for, with a
four-way output for each of the three areas it names:

    matched | probable_match | unmatched | (an exception_reason attached
    to the latter two, explaining what almost matched and why it didn't
    fully qualify)

### Bank
Matches bank_transactions to payments on amount, date, and counterparty
(entity + currency).

### AP
Matches invoices to payments on vendor, amount, and date -- deliberately
*not* using the schema's own payments.invoice_id foreign key to find
candidates, so this proves independent matching capability rather than
reading back a link the data already provides. Where a payment's actual
invoice_id disagrees with what this engine independently matched it to,
that's flagged as its own exception (a real data-integrity check on the
FK itself, not just a matching exercise).

### Intercompany
Matches transactions between entities on the entity pair, reference,
amount, currency, and period (the transaction's year-month) -- extending
Phase 9's reference+amount-only matching with the two extra keys PLAN.md
§26 asks for.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class MatchResult:
    subject_id: str
    match_status: str  # 'matched' | 'probable_match' | 'unmatched'
    matched_id: Optional[str] = None
    exception_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Bank
# ---------------------------------------------------------------------------

def reconcile_bank(
    bank_df: pd.DataFrame,
    payments_df: pd.DataFrame,
    tight_amount_tolerance: float = 0.01,
    tight_day_tolerance: int = 3,
    loose_amount_pct: float = 0.02,
    loose_day_tolerance: int = 10,
) -> list[MatchResult]:
    """For each bank transaction: a candidate payment matching on entity +
    currency, with amount and date both within the tight tolerances, is
    'matched'. Failing that, a candidate within the looser tolerances (a
    small amount variance -- bank fees, rounding -- or a wider date
    window) is 'probable_match'. No candidate at all is 'unmatched'.
    Greedy: tight matches are claimed first, across all transactions,
    before any probable_match is considered, so a strong match elsewhere
    can't be blocked by a weaker one claiming the same payment first."""
    bank = bank_df.copy()
    bank["transaction_date"] = pd.to_datetime(bank["transaction_date"])
    payments = payments_df.copy()
    payments["payment_date"] = pd.to_datetime(payments["payment_date"])

    def candidates(available, b, amount_tol, day_tol):
        return available[
            (available["entity_id"] == b["entity_id"])
            & (available["currency"] == b["currency"])
            & ((available["amount"] - b["amount"]).abs() <= amount_tol)
            & ((available["payment_date"] - b["transaction_date"]).abs() <= pd.Timedelta(days=day_tol))
        ]

    available = payments.copy()
    results: dict[str, MatchResult] = {}
    pending = []

    for _, b in bank.iterrows():
        tight = candidates(available, b, tight_amount_tolerance, tight_day_tolerance)
        if not tight.empty:
            best = tight.iloc[0]
            results[b["bank_transaction_id"]] = MatchResult(b["bank_transaction_id"], "matched", best["payment_id"])
            available = available.drop(best.name)
        else:
            pending.append(b)

    for b in pending:
        loose_tol = max(loose_amount_pct * abs(b["amount"]), tight_amount_tolerance)
        loose = candidates(available, b, loose_tol, loose_day_tolerance)
        if not loose.empty:
            best = loose.iloc[0]
            amount_diff = abs(best["amount"] - b["amount"])
            day_diff = abs((best["payment_date"] - b["transaction_date"]).days)
            reason = f"amount differs by {amount_diff:.2f}, date differs by {day_diff} day(s) -- outside tight tolerance"
            results[b["bank_transaction_id"]] = MatchResult(
                b["bank_transaction_id"], "probable_match", best["payment_id"], reason
            )
            available = available.drop(best.name)
        else:
            results[b["bank_transaction_id"]] = MatchResult(
                b["bank_transaction_id"], "unmatched", None,
                "no payment found for this entity/currency within the loose tolerance",
            )

    return list(results.values())


# ---------------------------------------------------------------------------
# AP
# ---------------------------------------------------------------------------

def reconcile_ap(
    invoices_df: pd.DataFrame,
    payments_df: pd.DataFrame,
    tight_amount_tolerance: float = 0.01,
    loose_amount_pct: float = 0.02,
    date_window_days: int = 90,
) -> list[MatchResult]:
    """For each AP invoice: a candidate 'made' payment for the same entity
    and currency, dated on or after the invoice date within
    `date_window_days`, with amount matching within tolerance, is
    'matched' (tight) or 'probable_match' (looser -- e.g. a partial
    payment or a small FX-rounding variance). No candidate is 'unmatched'
    (this invoice is still outstanding).

    Independent of payments.invoice_id by design (see module docstring):
    if a match found here disagrees with what that foreign key actually
    says, the result's exception_reason notes it as a data-integrity
    finding, not just a routine non-match.
    """
    invoices = invoices_df[invoices_df["invoice_type"] == "AP"].copy()
    invoices["invoice_date"] = pd.to_datetime(invoices["invoice_date"])
    payments = payments_df[payments_df["payment_type"] == "made"].copy()
    payments["payment_date"] = pd.to_datetime(payments["payment_date"])

    def candidates(available, inv, amount_tol):
        window_end = inv["invoice_date"] + pd.Timedelta(days=date_window_days)
        return available[
            (available["entity_id"] == inv["entity_id"])
            & (available["currency"] == inv["currency"])
            & ((available["amount"] - inv["amount"]).abs() <= amount_tol)
            & (available["payment_date"] >= inv["invoice_date"])
            & (available["payment_date"] <= window_end)
        ]

    available = payments.copy()
    results: list[MatchResult] = []
    pending = []

    for _, inv in invoices.iterrows():
        tight = candidates(available, inv, tight_amount_tolerance)
        if not tight.empty:
            best = tight.iloc[0]
            reason = _fk_mismatch_reason(inv, best)
            results.append(MatchResult(inv["invoice_id"], "matched", best["payment_id"], reason))
            available = available.drop(best.name)
        else:
            pending.append(inv)

    for inv in pending:
        loose_tol = max(loose_amount_pct * abs(inv["amount"]), tight_amount_tolerance)
        loose = candidates(available, inv, loose_tol)
        if not loose.empty:
            best = loose.iloc[0]
            amount_diff = abs(best["amount"] - inv["amount"])
            base_reason = f"payment amount differs by {amount_diff:.2f} -- possible partial payment or rounding"
            fk_reason = _fk_mismatch_reason(inv, best)
            reason = f"{base_reason}; {fk_reason}" if fk_reason else base_reason
            results.append(MatchResult(inv["invoice_id"], "probable_match", best["payment_id"], reason))
            available = available.drop(best.name)
        else:
            results.append(MatchResult(
                inv["invoice_id"], "unmatched", None,
                "no payment found within the amount/date window -- invoice still outstanding",
            ))

    return results


def _fk_mismatch_reason(invoice: pd.Series, matched_payment: pd.Series) -> Optional[str]:
    """If this payment's own invoice_id points somewhere other than the
    invoice we independently matched it to, that's a real discrepancy
    between the database's own link and this engine's reconciliation --
    worth surfacing, not silently trusting either side."""
    linked_invoice_id = matched_payment.get("invoice_id")
    if linked_invoice_id and linked_invoice_id != invoice["invoice_id"]:
        return (
            f"data-integrity note: payment {matched_payment['payment_id']}'s own invoice_id "
            f"points to {linked_invoice_id!r}, not this invoice -- independent match disagrees with the stored link"
        )
    return None


# ---------------------------------------------------------------------------
# Intercompany
# ---------------------------------------------------------------------------

def reconcile_intercompany(ic_df: pd.DataFrame, amount_tolerance: float = 0.01) -> list[MatchResult]:
    """For each intercompany transaction: its counterpart is the row with
    the reversed entity pair, the same reference, the same currency, and
    the same period (year-month of the transaction date). 'matched' if
    the counterpart's amount is within tolerance; 'probable_match' if a
    same-reference, same-entity-pair counterpart exists but the period or
    amount is off (a likely timing difference -- posted a few days either
    side of a period boundary); 'unmatched' if no counterpart exists at all.
    """
    df = ic_df.copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    df["period"] = df["transaction_date"].dt.to_period("M").astype(str)

    results: list[MatchResult] = []
    by_reference = df.groupby("reference")

    for reference, group in by_reference:
        if len(group) < 2:
            results.append(MatchResult(
                group.iloc[0]["intercompany_transaction_id"], "unmatched", None,
                f"no counterpart entry at all for reference {reference!r}",
            ))
            continue

        rows = group.to_dict(orient="records")
        for row in rows:
            counterpart = next(
                (r for r in rows
                 if r["intercompany_transaction_id"] != row["intercompany_transaction_id"]
                 and r["entity_from_id"] == row["entity_to_id"]
                 and r["entity_to_id"] == row["entity_from_id"]),
                None,
            )
            if counterpart is None:
                results.append(MatchResult(
                    row["intercompany_transaction_id"], "unmatched", None,
                    f"reference {reference!r} has another entry but not from the reversed entity pair",
                ))
                continue

            amount_diff = abs(row["amount"] - counterpart["amount"])
            same_period = row["period"] == counterpart["period"]
            same_currency = row["currency"] == counterpart["currency"]

            if amount_diff <= amount_tolerance and same_period and same_currency:
                results.append(MatchResult(
                    row["intercompany_transaction_id"], "matched", counterpart["intercompany_transaction_id"],
                ))
            else:
                reasons = []
                if amount_diff > amount_tolerance:
                    reasons.append(f"amount differs by {amount_diff:.2f}")
                if not same_period:
                    reasons.append(f"periods differ ({row['period']} vs {counterpart['period']})")
                if not same_currency:
                    reasons.append(f"currencies differ ({row['currency']} vs {counterpart['currency']})")
                results.append(MatchResult(
                    row["intercompany_transaction_id"], "probable_match", counterpart["intercompany_transaction_id"],
                    "; ".join(reasons),
                ))

    return results
