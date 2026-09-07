"""Schema validation (Phase 9, PLAN.md §21).

Structural/type checks only -- is this a real date, a recognised currency
code, a positive amount, one of the allowed status values -- using Pydantic
models. Business-rule problems that are still perfectly well-typed (a blank
entity_code, an unresolvable vendor, a duplicate invoice number) are
deliberately NOT caught here: those are data-quality and mapping concerns,
handled by mappings.py and reconciliation.py, and logged as their own
exception categories rather than lumped in with "malformed data".
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
from pydantic import BaseModel, ValidationError, field_validator

VALID_CURRENCIES = {"GBP", "USD"}


class InvoiceRow(BaseModel):
    invoice_id: str
    invoice_type: str
    invoice_number: str
    entity_code: Optional[str] = None
    customer_code: Optional[str] = None
    vendor_code: Optional[str] = None
    vendor_name_raw: Optional[str] = None
    invoice_date: date
    due_date: Optional[date] = None
    currency: str
    amount: float
    source: str
    account_code: Optional[str] = None
    status: str

    @field_validator("invoice_type")
    @classmethod
    def _invoice_type_valid(cls, v: str) -> str:
        if v not in {"AR", "AP"}:
            raise ValueError(f"invoice_type must be AR or AP, got {v!r}")
        return v

    @field_validator("currency")
    @classmethod
    def _currency_known(cls, v: str) -> str:
        if v not in VALID_CURRENCIES:
            raise ValueError(f"unrecognised currency {v!r}")
        return v

    @field_validator("amount")
    @classmethod
    def _amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"amount must be positive, got {v}")
        return v


class PaymentRow(BaseModel):
    payment_id: str
    entity_code: Optional[str] = None
    invoice_id: Optional[str] = None
    payment_date: date
    currency: str
    amount: float
    payment_type: str
    source: str
    status: str

    @field_validator("currency")
    @classmethod
    def _currency_known(cls, v: str) -> str:
        if v not in VALID_CURRENCIES:
            raise ValueError(f"unrecognised currency {v!r}")
        return v

    @field_validator("payment_type")
    @classmethod
    def _payment_type_valid(cls, v: str) -> str:
        if v not in {"received", "made"}:
            raise ValueError(f"payment_type must be received or made, got {v!r}")
        return v

    @field_validator("amount")
    @classmethod
    def _amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"amount must be positive, got {v}")
        return v


class BankTransactionRow(BaseModel):
    bank_transaction_id: str
    entity_code: Optional[str] = None
    bank_account_code: str
    transaction_date: date
    currency: str
    amount: float  # can be negative (bank charges)
    description: Optional[str] = None
    source: str
    match_status: str
    matched_payment_id: Optional[str] = None

    @field_validator("currency")
    @classmethod
    def _currency_known(cls, v: str) -> str:
        if v not in VALID_CURRENCIES:
            raise ValueError(f"unrecognised currency {v!r}")
        return v


class IntercompanyRow(BaseModel):
    intercompany_transaction_id: str
    entity_from_code: str
    entity_to_code: str
    transaction_date: date
    currency: str
    amount: float
    reference: str
    source: str
    match_status: str
    related_journal_entry_id: Optional[str] = None

    @field_validator("currency")
    @classmethod
    def _currency_known(cls, v: str) -> str:
        if v not in VALID_CURRENCIES:
            raise ValueError(f"unrecognised currency {v!r}")
        return v

    @field_validator("amount")
    @classmethod
    def _amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"amount must be positive, got {v}")
        return v


def validate_rows(df: pd.DataFrame, model: type[BaseModel]) -> tuple[list[dict], list[dict]]:
    """Validate every row of df against a Pydantic model.

    Returns (valid_records, errors). valid_records are plain dicts
    (model.model_dump()); errors are {row_index, id_hint, errors} dicts
    suitable for the exception report.
    """
    valid: list[dict] = []
    errors: list[dict] = []
    # df.where(df.notna(), None) doesn't reliably turn NaN into None across
    # pandas versions/dtypes, so clean each cell explicitly instead.
    records = [
        {k: (None if pd.isna(v) else v) for k, v in row.items()}
        for row in df.to_dict(orient="records")
    ]

    for idx, row in enumerate(records):
        try:
            obj = model(**row)
            valid.append(obj.model_dump())
        except ValidationError as exc:
            id_hint = next(
                (row[k] for k in ("invoice_id", "payment_id", "bank_transaction_id",
                                   "intercompany_transaction_id") if k in row),
                None,
            )
            errors.append({"row_index": idx, "id_hint": id_hint, "errors": exc.errors()})

    return valid, errors
