"""Request/response schemas (Pydantic) for the REST API (PLAN.md §22).

Naming convention: *Create for a POST request body, *Out for what comes
back. Business keys (entity_code, customer_code, ...) are used everywhere
in the API surface, never the database's internal surrogate IDs -- a
client integrating with this API shouldn't need to know Northstar's
internal ID scheme, the same way a real ERP's integration layer exposes
codes, not row IDs.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, model_validator

VALID_CURRENCIES = {"GBP", "USD"}


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

class CustomerCreate(BaseModel):
    customer_code: str
    customer_name: str
    entity_code: str
    billing_currency: str = Field(pattern="^(GBP|USD)$")


class CustomerOut(BaseModel):
    customer_id: str
    customer_code: str
    customer_name: str
    entity_code: str
    billing_currency: str
    status: str


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------

class InvoiceCreate(BaseModel):
    invoice_type: str = Field(pattern="^(AR|AP)$")
    invoice_number: str
    entity_code: str
    customer_code: Optional[str] = None
    vendor_code: Optional[str] = None
    invoice_date: date
    due_date: Optional[date] = None
    currency: str = Field(pattern="^(GBP|USD)$")
    amount: float = Field(gt=0)
    source: str
    account_code: Optional[str] = None

    @model_validator(mode="after")
    def _party_matches_type(self) -> "InvoiceCreate":
        if self.invoice_type == "AR" and not self.customer_code:
            raise ValueError("AR invoices require customer_code")
        if self.invoice_type == "AP" and not self.vendor_code:
            raise ValueError("AP invoices require vendor_code")
        return self


class InvoiceOut(BaseModel):
    invoice_id: str
    invoice_type: str
    invoice_number: str
    entity_code: str
    customer_code: Optional[str] = None
    vendor_code: Optional[str] = None
    invoice_date: date
    due_date: Optional[date] = None
    currency: str
    amount: float
    source: str
    account_code: Optional[str] = None
    status: str
    idempotent_replay: bool = Field(
        default=False,
        description="True if this response is an existing invoice returned "
                    "in place of creating a duplicate (see POST /invoices).",
    )


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

class PaymentCreate(BaseModel):
    entity_code: str
    invoice_id: Optional[str] = None
    payment_date: date
    currency: str = Field(pattern="^(GBP|USD)$")
    amount: float = Field(gt=0)
    payment_type: str = Field(pattern="^(received|made)$")
    source: str


class PaymentOut(BaseModel):
    payment_id: str
    entity_code: str
    invoice_id: Optional[str] = None
    payment_date: date
    currency: str
    amount: float
    payment_type: str
    source: str
    status: str


# ---------------------------------------------------------------------------
# Journal entries
# ---------------------------------------------------------------------------

class JournalLineCreate(BaseModel):
    account_code: str
    debit_amount: float = Field(ge=0, default=0)
    credit_amount: float = Field(ge=0, default=0)
    line_description: Optional[str] = None

    @model_validator(mode="after")
    def _exactly_one_side(self) -> "JournalLineCreate":
        if (self.debit_amount > 0) == (self.credit_amount > 0):
            raise ValueError("each line must have exactly one of debit_amount/credit_amount > 0")
        return self


class JournalEntryCreate(BaseModel):
    entity_code: str
    entry_date: date
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    currency: str = Field(pattern="^(GBP|USD)$")
    source: str = Field(pattern="^(system|manual|ai_assisted)$")
    classification: str
    created_by: str
    approved_by: Optional[str] = None
    description: Optional[str] = None
    lines: list[JournalLineCreate] = Field(min_length=2)

    @model_validator(mode="after")
    def _balanced_and_maker_checker(self) -> "JournalEntryCreate":
        total_debit = round(sum(l.debit_amount for l in self.lines), 2)
        total_credit = round(sum(l.credit_amount for l in self.lines), 2)
        if total_debit != total_credit:
            raise ValueError(f"journal entry is not balanced: debits {total_debit} != credits {total_credit}")
        if self.approved_by is not None and self.approved_by == self.created_by:
            raise ValueError("approved_by cannot equal created_by (maker/checker violation)")
        return self


class JournalLineOut(BaseModel):
    journal_line_id: str
    account_code: str
    debit_amount: float
    credit_amount: float
    line_description: Optional[str] = None


class JournalEntryOut(BaseModel):
    journal_entry_id: str
    entity_code: str
    entry_date: date
    period: str
    currency: str
    source: str
    classification: str
    status: str
    created_by: str
    approved_by: Optional[str] = None
    description: Optional[str] = None
    lines: list[JournalLineOut]


# ---------------------------------------------------------------------------
# Reporting (GET endpoints)
# ---------------------------------------------------------------------------

class TrialBalanceRow(BaseModel):
    entity_code: str
    account_code: str
    account_name: str
    account_type: str
    debit_total: float
    credit_total: float
    net_balance: float


class ReconciliationStatusRow(BaseModel):
    entity_code: str
    matched_count: int
    total_count: int
    reconciliation_rate_pct: float


class CloseStatusRow(BaseModel):
    entity_code: str
    period: str
    total_journals: int
    posted_count: int
    pending_count: int
    close_complete_pct: float


class IntercompanyExceptionRow(BaseModel):
    intercompany_transaction_id: str
    entity_from_code: str
    entity_to_code: str
    transaction_date: date
    currency: str
    amount: float
    reference: str
