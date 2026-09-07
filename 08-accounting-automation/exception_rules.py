"""Deterministic exception rules (Phase 11, PLAN.md §23).

Each function answers "is this record clean, or does it need a human"? -
duplicate invoices, missing required fields, and intercompany transactions
with no counterpart. This deliberately reimplements small, focused
versions of checks that already exist in 06-python/reconciliation.py
(duplicate detection) rather than importing across phases: 06-python's
version is built for cleaning a messy source file during ingestion, this
one is framed as a standing accounting policy check that could just as
well run against already-loaded, otherwise-clean data (e.g. a
resubmission through the API) -- same idea, different point in the
pipeline, so kept as its own small module rather than a cross-import
between two directories that aren't even valid Python package names.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional


@dataclass
class Exception_:  # noqa: N801 -- `Exception` alone would shadow the builtin
    rule: str
    id: str
    detail: str


def check_duplicate_invoices(invoices: list[dict]) -> list[Exception_]:
    """invoices: dicts with at least invoice_id, entity_id, invoice_number,
    invoice_type. Flags every row after the first sharing the same
    (entity_id, invoice_number, invoice_type) -- matches PLAN.md's
    "duplicate invoice -> exception" rule."""
    seen: dict[tuple, str] = {}
    exceptions = []
    for row in sorted(invoices, key=lambda r: r["invoice_id"]):
        key = (row["entity_id"], row["invoice_number"], row["invoice_type"])
        if key in seen:
            exceptions.append(Exception_(
                rule="duplicate_invoice",
                id=row["invoice_id"],
                detail=f"duplicate of {seen[key]} on (entity, invoice_number, invoice_type)",
            ))
        else:
            seen[key] = row["invoice_id"]
    return exceptions


REQUIRED_INVOICE_FIELDS = ("entity_id", "invoice_date", "currency", "amount", "status")


def check_required_fields(invoice: dict) -> list[Exception_]:
    """Missing-required-metadata check. PLAN.md §23 lists "missing tax
    field -> exception" as its example; this project's data model (see
    data-model.md) doesn't track a separate tax field, so this checks the
    fields data-model.md actually declares mandatory on every transaction
    (entity, date, currency, source, classification, status) instead --
    same category of rule, applied to what this schema actually has."""
    exceptions = []
    for field in REQUIRED_INVOICE_FIELDS:
        if invoice.get(field) in (None, ""):
            exceptions.append(Exception_(
                rule="missing_required_field",
                id=invoice.get("invoice_id", "unknown"),
                detail=f"required field {field!r} is missing",
            ))
    if invoice.get("invoice_type") == "AR" and not invoice.get("customer_id"):
        exceptions.append(Exception_(
            rule="missing_required_field", id=invoice.get("invoice_id", "unknown"),
            detail="AR invoice has no customer_id",
        ))
    if invoice.get("invoice_type") == "AP" and not invoice.get("vendor_id"):
        exceptions.append(Exception_(
            rule="missing_required_field", id=invoice.get("invoice_id", "unknown"),
            detail="AP invoice has no vendor_id",
        ))
    return exceptions


def check_intercompany_counterpart(transactions: list[dict], amount_tolerance: float = 0.01) -> list[Exception_]:
    """transactions: dicts with intercompany_transaction_id, reference,
    amount. A reference is validated only if at least two rows share it
    with amounts within tolerance -- matches PLAN.md's "intercompany
    transaction -> counterpart validation" rule (R04)."""
    by_reference: dict[str, list[dict]] = defaultdict(list)
    for row in transactions:
        by_reference[row["reference"]].append(row)

    exceptions = []
    for reference, rows in by_reference.items():
        if len(rows) < 2:
            exceptions.append(Exception_(
                rule="intercompany_no_counterpart", id=rows[0]["intercompany_transaction_id"],
                detail=f"reference {reference!r} has no counterpart entry",
            ))
            continue
        amounts = [r["amount"] for r in rows]
        if max(amounts) - min(amounts) > amount_tolerance:
            for row in rows:
                exceptions.append(Exception_(
                    rule="intercompany_amount_mismatch", id=row["intercompany_transaction_id"],
                    detail=f"reference {reference!r} has mismatched amounts across sides: {amounts}",
                ))
    return exceptions


# Added after Phase 12's evaluation surfaced a real gap (see
# invoice_classification.py's check_amount_outlier for the other half of
# the response): a transaction that is a genuine anomaly matching NOTHING
# observable -- not an amount outlier, not a hallucination, not a
# deterministic mismatch -- cannot be caught by any per-transaction rule,
# by definition. The only real answer to that category, and the one real
# audit/SOX programs actually use, is periodically sampling even the
# "clean" auto-approved population, not just the flagged one.
DEFAULT_AUDIT_SAMPLE_RATE = 0.05  # documented assumption: 1 in 20, not a validated policy figure


def should_sample_for_audit(transaction_id: str, sample_rate: float = DEFAULT_AUDIT_SAMPLE_RATE) -> bool:
    """Deterministic (not random) so the same transaction_id always gets
    the same answer -- reproducible for tests and for explaining after the
    fact *why* a given transaction was pulled, without having to have
    logged a coin-flip at the time. Hashes the ID into a value spread
    uniformly over [0, 1) and compares it to sample_rate, so across many
    transaction_ids the selected fraction converges on sample_rate."""
    digest = hashlib.sha256(transaction_id.encode()).hexdigest()
    position = int(digest[:8], 16) / 0xFFFFFFFF
    return position < sample_rate
