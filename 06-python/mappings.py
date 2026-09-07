"""Entity, customer, vendor, and account mapping (Phase 9, PLAN.md §21).

Resolves the natural business keys in raw source data (entity_code,
customer_code, vendor_code, account_code) into the surrogate IDs the
schema in 03-architecture/data-model.md actually uses.

Vendor resolution is the one genuinely fuzzy step: AP invoices arrive with
a vendor_name_raw that doesn't always match the vendor master exactly (see
04-data/data-quality-log.md's "Inconsistent Vendor Name" issues, e.g. "Med
Supplies Ltd" vs "Medical Supplies Ltd"). 05-sql/seed.sql's plain SQL join
had to drop those rows entirely; this module recovers them with a
same-string fuzzy match instead, using Python's built-in difflib rather
than adding a new dependency.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field

import pandas as pd

# Below this similarity ratio (0-1), a vendor name is treated as
# genuinely unresolved rather than guessed at -- see test_mappings.py for
# the specific pairs this threshold is tuned against.
FUZZY_MATCH_CUTOFF = 0.75


@dataclass
class ReferenceData:
    entities_by_code: dict[str, str]
    customers_by_code: dict[str, str]
    vendors_by_code: dict[str, str]
    vendors_by_name: dict[str, str] = field(default_factory=dict)  # lowercased name -> vendor_id
    vendor_names: list[str] = field(default_factory=list)  # canonical names, for fuzzy matching
    accounts_by_code: dict[str, str] = field(default_factory=dict)


def load_reference_data(engine) -> ReferenceData:
    entities = pd.read_sql("SELECT entity_id, entity_code FROM entities", engine)
    customers = pd.read_sql("SELECT customer_id, customer_code FROM customers", engine)
    vendors = pd.read_sql("SELECT vendor_id, vendor_code, vendor_name FROM vendors", engine)
    accounts = pd.read_sql("SELECT account_id, account_code FROM chart_of_accounts", engine)

    return ReferenceData(
        entities_by_code=dict(zip(entities["entity_code"], entities["entity_id"])),
        customers_by_code=dict(zip(customers["customer_code"], customers["customer_id"])),
        vendors_by_code=dict(zip(vendors["vendor_code"], vendors["vendor_id"])),
        vendors_by_name={name.lower(): vid for vid, name in zip(vendors["vendor_id"], vendors["vendor_name"])},
        vendor_names=list(vendors["vendor_name"]),
        accounts_by_code=dict(zip(accounts["account_code"], accounts["account_id"])),
    )


def _blank(value) -> bool:
    """True for None, '', and NaN. A pandas DataFrame built from a list of
    dicts silently turns a Python None into a float NaN whenever the same
    column also has string values elsewhere -- and NaN is truthy in plain
    Python, so a simple `if not value` check alone lets it slip through."""
    if value is None:
        return True
    if isinstance(value, float) and value != value:  # NaN != NaN
        return True
    return value == ""


def map_entity(entity_code: str | None, ref: ReferenceData) -> str | None:
    if _blank(entity_code):
        return None
    return ref.entities_by_code.get(entity_code)


def map_customer(customer_code: str | None, ref: ReferenceData) -> str | None:
    if _blank(customer_code):
        return None
    return ref.customers_by_code.get(customer_code)


def map_account(account_code: str | None, ref: ReferenceData) -> str | None:
    if _blank(account_code):
        return None
    return ref.accounts_by_code.get(account_code)


def map_vendor(vendor_code: str | None, vendor_name_raw: str | None, ref: ReferenceData) -> tuple[str | None, str]:
    """Resolve a vendor. Returns (vendor_id, method); vendor_id is None if
    unresolved. method is 'exact_code', 'fuzzy_name', or 'unresolved'."""
    if not _blank(vendor_code):
        vendor_id = ref.vendors_by_code.get(vendor_code)
        if vendor_id:
            return vendor_id, "exact_code"

    if not _blank(vendor_name_raw):
        candidates = difflib.get_close_matches(vendor_name_raw, ref.vendor_names, n=1, cutoff=FUZZY_MATCH_CUTOFF)
        if candidates:
            vendor_id = ref.vendors_by_name.get(candidates[0].lower())
            if vendor_id:
                return vendor_id, "fuzzy_name"

    return None, "unresolved"
