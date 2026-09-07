"""Deterministic invoice classification rules (Phase 11, PLAN.md §23).

Answers three questions about an already-mapped invoice (entity, vendor/
customer, and account already resolved to real IDs by 06-python/mappings.py
or 07-api/models.py -- classification assumes that resolution already
happened, it doesn't redo it):

1. Vendor -> account mapping: does the account actually used on this AP
   invoice match the vendor's default account? A mismatch isn't
   auto-corrected -- a human may have deliberately coded it differently --
   it's flagged so a person confirms it, the same "detect, don't silently
   fix" stance 06-python/reconciliation.py takes on duplicates.
2. Entity -> ledger: trivial with a single shared chart of accounts (every
   entity posts to the same ledger), but still checked explicitly rather
   than assumed, since a real multi-CoA rollout wouldn't have this luxury.
3. Currency -> FX requirement: does this transaction's currency differ
   from the entity's functional currency, meaning FX conversion applies
   before it can be reported in the entity's own currency?

These are exactly the deterministic checks PLAN.md's critical distinction
(§23) puts before any AI involvement: "rules should handle deterministic
accounting controls; AI should assist with ambiguous classification only."
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class AccountMappingResult:
    suggested_account_id: Optional[str]
    matches_vendor_default: bool
    exception: Optional[str] = None


def classify_vendor_account(vendor_default_account_id: Optional[str], invoice_account_id: Optional[str]) -> AccountMappingResult:
    """Check (never silently correct) an AP invoice's account against the
    vendor's default. Three outcomes:

    - invoice has no account at all -> suggest the vendor's default, no
      exception (there's nothing to contradict yet)
    - invoice's account matches the vendor default -> confirmed, no
      exception
    - invoice's account differs from the vendor default -> flagged for
      human review, vendor default returned as the suggestion
    """
    if invoice_account_id is None:
        return AccountMappingResult(suggested_account_id=vendor_default_account_id, matches_vendor_default=True)

    if vendor_default_account_id is None:
        # vendor has no default on file -- nothing to check against
        return AccountMappingResult(suggested_account_id=invoice_account_id, matches_vendor_default=True)

    if invoice_account_id == vendor_default_account_id:
        return AccountMappingResult(suggested_account_id=invoice_account_id, matches_vendor_default=True)

    return AccountMappingResult(
        suggested_account_id=vendor_default_account_id,
        matches_vendor_default=False,
        exception=(
            f"invoice account {invoice_account_id!r} does not match vendor's default "
            f"account {vendor_default_account_id!r}"
        ),
    )


def validate_entity_ledger(entity_id: Optional[str]) -> Optional[str]:
    """Every entity shares one chart of accounts (see data-model.md), so
    there's no per-entity ledger selection to get wrong -- but a missing
    entity_id means there's no ledger to post to at all. Returns an
    exception string, or None if fine."""
    if entity_id is None:
        return "no entity resolved -- cannot determine which ledger this posts to"
    return None


def requires_fx_conversion(transaction_currency: str, entity_functional_currency: str) -> bool:
    """A transaction in anything other than its entity's functional
    currency needs FX conversion before it can be reported in that
    entity's own books (R08) -- see 06-python/transformations.py for the
    actual conversion, this only flags that it's needed."""
    return transaction_currency != entity_functional_currency
