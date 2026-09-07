"""Generate synthetic Northstar Finance OS source data (Phase 7, PLAN.md §19).

Produces the raw, pre-ingestion CSV extracts that would arrive from Billing,
Banking, AP, and the legacy ERP, using the field names defined in
03-architecture/data-model.md. The data is deliberately messy in the exact
ways PLAN.md §19 calls for: duplicate invoices, missing entity codes,
inconsistent vendor names, GBP and USD transactions, unmatched bank
transactions, unmatched intercompany transactions, incorrect account
mappings, duplicate payments, missing invoice references, manual journal
entries, and late transactions. This messiness is what gives the Phase 9
validation/ingestion pipeline and the Phase 13 reconciliation engine
something real to catch.

Scale: ~300 transactions across three close periods (2026-06 to 2026-08),
a deliberately-readable subset of the ~5,000/month figure in AGENTS.md's
fictional client profile, chosen so the CSVs stay easy to review by hand.

Every planted data-quality issue is logged to data-quality-log.md as it is
created, so later phases can be checked against a known ground truth
instead of guessing whether their detection logic actually works.

All data is entirely fictional. See AGENTS.md's no-real-data rule --
never substitute real customer, vendor, or employer data here.

Run: python 04-data/generate_data.py
Deterministic: a fixed random seed means re-running reproduces the same
CSVs byte-for-byte, so the dataset is a stable basis for later phases.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

SEED = 42
random.seed(SEED)

OUTPUT_DIR = Path(__file__).parent
PERIODS = ["2026-06", "2026-07", "2026-08"]
CURRENT_CLOSE_PERIOD = "2026-08"

# Every deliberately-planted data-quality issue is recorded here as it's
# created, then written out to data-quality-log.md at the end of the run.
issues: list[dict] = []


def log_issue(category: str, table: str, ids: str, description: str) -> None:
    issues.append({"category": category, "table": table, "ids": ids, "description": description})


def month_bounds(period: str) -> tuple[date, date]:
    year, month = (int(p) for p in period.split("-"))
    start = date(year, month, 1)
    end = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    return start, end


def random_date_in(period: str) -> date:
    start, end = month_bounds(period)
    return start + timedelta(days=random.randint(0, (end - start).days))


# ---------------------------------------------------------------------------
# Entities (fixed -- matches AGENTS.md's fictional client profile exactly)
# ---------------------------------------------------------------------------

ENTITIES = [
    {"entity_id": "ENT-001", "entity_code": "NHH-UK", "entity_name": "Northstar Health Holdings Ltd",
     "country": "United Kingdom", "functional_currency": "GBP", "status": "active"},
    {"entity_id": "ENT-002", "entity_code": "NHS-US", "entity_name": "Northstar Health Services Inc",
     "country": "United States", "functional_currency": "USD", "status": "active"},
    {"entity_id": "ENT-003", "entity_code": "NSS-UK", "entity_name": "Northstar Shared Services Ltd",
     "country": "United Kingdom", "functional_currency": "GBP", "status": "active"},
]
ENTITY_CODES = [e["entity_code"] for e in ENTITIES]
ENTITY_CURRENCY = {e["entity_code"]: e["functional_currency"] for e in ENTITIES}

# ---------------------------------------------------------------------------
# Chart of accounts (single, shared CoA -- fixes today's per-entity drift)
# ---------------------------------------------------------------------------

CHART_OF_ACCOUNTS = [
    {"account_code": "1000", "account_name": "Cash and Cash Equivalents", "account_type": "asset", "normal_balance": "debit"},
    {"account_code": "1010", "account_name": "Accounts Receivable", "account_type": "asset", "normal_balance": "debit"},
    {"account_code": "1020", "account_name": "Prepaid Expenses", "account_type": "asset", "normal_balance": "debit"},
    {"account_code": "1030", "account_name": "Intercompany Receivable", "account_type": "asset", "normal_balance": "debit"},
    {"account_code": "1040", "account_name": "Fixed Assets - Equipment", "account_type": "asset", "normal_balance": "debit"},
    {"account_code": "2000", "account_name": "Accounts Payable", "account_type": "liability", "normal_balance": "credit"},
    {"account_code": "2010", "account_name": "Accrued Expenses", "account_type": "liability", "normal_balance": "credit"},
    {"account_code": "2020", "account_name": "Intercompany Payable", "account_type": "liability", "normal_balance": "credit"},
    {"account_code": "2030", "account_name": "Accrued Payroll", "account_type": "liability", "normal_balance": "credit"},
    {"account_code": "2040", "account_name": "VAT / Sales Tax Payable", "account_type": "liability", "normal_balance": "credit"},
    {"account_code": "3000", "account_name": "Share Capital", "account_type": "equity", "normal_balance": "credit"},
    {"account_code": "3010", "account_name": "Retained Earnings", "account_type": "equity", "normal_balance": "credit"},
    {"account_code": "4000", "account_name": "Patient Services Revenue", "account_type": "revenue", "normal_balance": "credit"},
    {"account_code": "4010", "account_name": "Insurance Reimbursement Revenue", "account_type": "revenue", "normal_balance": "credit"},
    {"account_code": "4020", "account_name": "Corporate Wellness Revenue", "account_type": "revenue", "normal_balance": "credit"},
    {"account_code": "4030", "account_name": "Other Operating Revenue", "account_type": "revenue", "normal_balance": "credit"},
    {"account_code": "5000", "account_name": "Medical Supplies Expense", "account_type": "expense", "normal_balance": "debit"},
    {"account_code": "5010", "account_name": "Facilities Expense", "account_type": "expense", "normal_balance": "debit"},
    {"account_code": "5020", "account_name": "IT & Software Expense", "account_type": "expense", "normal_balance": "debit"},
    {"account_code": "5030", "account_name": "Payroll Expense", "account_type": "expense", "normal_balance": "debit"},
    {"account_code": "5040", "account_name": "Professional Fees", "account_type": "expense", "normal_balance": "debit"},
    {"account_code": "5050", "account_name": "Depreciation Expense", "account_type": "expense", "normal_balance": "debit"},
    {"account_code": "5060", "account_name": "FX Revaluation Expense", "account_type": "expense", "normal_balance": "debit"},
    {"account_code": "5070", "account_name": "Bank Charges", "account_type": "expense", "normal_balance": "debit"},
    {"account_code": "5090", "account_name": "Office Supplies Expense", "account_type": "expense", "normal_balance": "debit"},
]
for i, acc in enumerate(CHART_OF_ACCOUNTS, start=1):
    acc["account_id"] = f"ACC-{i:03d}"
    acc["status"] = "active"

EXPENSE_ACCOUNTS = [a["account_code"] for a in CHART_OF_ACCOUNTS if a["account_type"] == "expense"]

# ---------------------------------------------------------------------------
# Customers (AR master data -- billed via the billing platform)
# ---------------------------------------------------------------------------

CUSTOMER_NAMES = [
    "Anthem Health Partners", "Bright Path Insurance Co", "Meridian Corporate Wellness",
    "Lakeside Employer Health Plan", "Horizon Diagnostics Network", "Coastal Regional Insurers",
    "Summit Corporate Health", "Fairview Mutual Insurance", "Riverside Employer Group",
    "Northgate Insurance Partners", "Clearwater Health Alliance", "Pinecrest Corporate Benefits",
    "Ashford Mutual Health", "Bellmont Insurance Group", "Cedarview Employer Plan",
]
CUSTOMERS = []
for i, name in enumerate(CUSTOMER_NAMES, start=1):
    entity_code = random.choice(ENTITY_CODES)
    CUSTOMERS.append({
        "customer_id": f"CUST-{i:03d}",
        "customer_code": f"C{i:04d}",
        "customer_name": name,
        "entity_code": entity_code,
        "billing_currency": ENTITY_CURRENCY[entity_code],
        "status": "active",
    })

# ---------------------------------------------------------------------------
# Vendors (AP master data). "Medical Supplies Ltd" is the vendor deliberately
# used to demonstrate the inconsistent-vendor-name problem on AP invoices.
# ---------------------------------------------------------------------------

VENDORS = [
    {"vendor_name": "Medical Supplies Ltd", "default_account_code": "5000"},
    {"vendor_name": "Apex Facilities Management", "default_account_code": "5010"},
    {"vendor_name": "Bluewater IT Services", "default_account_code": "5020"},
    {"vendor_name": "Sterling Diagnostics Equipment", "default_account_code": "1040"},
    {"vendor_name": "Crestline Office Solutions", "default_account_code": "5090"},
    {"vendor_name": "Harborview Cleaning Services", "default_account_code": "5010"},
    {"vendor_name": "Prime Medical Devices Inc", "default_account_code": "5000"},
    {"vendor_name": "National Payroll Services", "default_account_code": "5040"},
    {"vendor_name": "Grantham Legal Partners", "default_account_code": "5040"},
    {"vendor_name": "Oakridge Laboratory Supplies", "default_account_code": "5000"},
    {"vendor_name": "Vantage Software Solutions", "default_account_code": "5020"},
    {"vendor_name": "Union Linen & Uniform Services", "default_account_code": "5010"},
]
for i, v in enumerate(VENDORS, start=1):
    v["vendor_id"] = f"VEND-{i:03d}"
    v["vendor_code"] = f"V{i:04d}"
    v["status"] = "active"

VENDOR_NAME_VARIANTS = {
    "Medical Supplies Ltd": ["Med Supplies Ltd", "Medical Supplies Limited"],
}

# ---------------------------------------------------------------------------
# FX rates -- one documented rate per week, per R08 (defined, auditable
# rate source; replaces today's undocumented month-end Excel spot rate)
# ---------------------------------------------------------------------------

fx_rates = []
fx_counter = 1
d = date(2026, 6, 1)
end_of_range = date(2026, 8, 31)
base_rate = 1.27
while d <= end_of_range:
    base_rate += random.uniform(-0.01, 0.01)
    fx_rates.append({
        "fx_rate_id": f"FX-{fx_counter:03d}",
        "currency_from": "GBP",
        "currency_to": "USD",
        "rate_date": d.isoformat(),
        "rate": round(base_rate, 4),
        "source": "Bank of England weekly reference rate",
    })
    fx_counter += 1
    d += timedelta(days=7)

# ---------------------------------------------------------------------------
# Invoices (AR from Billing, AP from AP) -- raw, pre-ingestion form
# ---------------------------------------------------------------------------

invoices: list[dict] = []
inv_counter = 1


def new_invoice_id() -> str:
    global inv_counter
    inv_id = f"INV-{inv_counter:04d}"
    inv_counter += 1
    return inv_id


for period in PERIODS:
    # AR invoices, one per customer per period (roughly)
    for cust in CUSTOMERS:
        if random.random() < 0.85:  # not every customer bills every month
            entity_code = cust["entity_code"]
            invoice_date = random_date_in(period)
            row = {
                "invoice_id": new_invoice_id(),
                "invoice_type": "AR",
                "invoice_number": f"{entity_code}-AR-{period.replace('-', '')}-{cust['customer_code']}",
                "entity_code": entity_code,
                "customer_code": cust["customer_code"],
                "vendor_code": "",
                "vendor_name_raw": "",
                "invoice_date": invoice_date.isoformat(),
                "due_date": (invoice_date + timedelta(days=30)).isoformat(),
                "currency": cust["billing_currency"],
                "amount": round(random.uniform(2000, 45000), 2),
                "source": "billing_api",
                "account_code": random.choice(["4000", "4010", "4020", "4030"]),
                "status": "open",
                "period": period,
            }
            invoices.append(row)

    # AP invoices, roughly two per vendor per period
    for vend in VENDORS:
        for _ in range(random.choice([1, 1, 2])):
            entity_code = random.choice(ENTITY_CODES)
            invoice_date = random_date_in(period)
            canonical_name = vend["vendor_name"]
            variants = VENDOR_NAME_VARIANTS.get(canonical_name)
            use_variant = variants is not None and random.random() < 0.4
            vendor_name_raw = random.choice(variants) if use_variant else canonical_name
            vendor_code = "" if use_variant else vend["vendor_code"]
            account_code = vend["default_account_code"]
            row = {
                "invoice_id": new_invoice_id(),
                "invoice_type": "AP",
                "invoice_number": f"{entity_code}-AP-{period.replace('-', '')}-{vend['vendor_code']}-{random.randint(100,999)}",
                "entity_code": entity_code,
                "customer_code": "",
                "vendor_code": vendor_code,
                "vendor_name_raw": vendor_name_raw,
                "invoice_date": invoice_date.isoformat(),
                "due_date": (invoice_date + timedelta(days=30)).isoformat(),
                "currency": ENTITY_CURRENCY[entity_code],
                "amount": round(random.uniform(150, 12000), 2),
                "source": "ap_email_pdf",
                "account_code": account_code,
                "status": "open",
                "period": period,
            }
            invoices.append(row)
            if use_variant:
                log_issue("inconsistent_vendor_name", "invoices", row["invoice_id"],
                          f"vendor_name_raw '{vendor_name_raw}' does not match master vendor "
                          f"'{canonical_name}' (vendor_code left unmapped) -- expected fuzzy match "
                          f"in Phase 9 ingestion")

# Duplicate invoices: re-key the same AR/AP invoice a second time
dup_candidates = random.sample(invoices, 6)
for src in dup_candidates:
    dup = dict(src)
    dup["invoice_id"] = new_invoice_id()
    if random.random() < 0.5:
        # exact re-export duplicate
        pass
    else:
        # re-keying error: amount typo'd slightly on the second entry
        dup["amount"] = round(dup["amount"] + random.choice([-0.01, 0.01]) * random.randint(1, 50), 2)
    invoices.append(dup)
    log_issue("duplicate_invoice", "invoices", f"{src['invoice_id']}, {dup['invoice_id']}",
              f"same invoice_number '{src['invoice_number']}' re-keyed under a second invoice_id")

# Missing entity codes
missing_entity_targets = random.sample(invoices, 4)
for row in missing_entity_targets:
    row["entity_code"] = ""
    log_issue("missing_entity_code", "invoices", row["invoice_id"], "entity_code blank at source")

# Incorrect account mappings: AP invoice coded to a plausible-but-wrong expense account
ap_invoices = [r for r in invoices if r["invoice_type"] == "AP" and r["account_code"] in EXPENSE_ACCOUNTS]
wrong_account_targets = random.sample(ap_invoices, 5)
for row in wrong_account_targets:
    wrong_choices = [a for a in EXPENSE_ACCOUNTS if a != row["account_code"]]
    old = row["account_code"]
    row["account_code"] = random.choice(wrong_choices)
    log_issue("incorrect_account_mapping", "invoices", row["invoice_id"],
              f"coded to {row['account_code']} instead of the vendor's mapped account {old}")

# Missing invoice references seeded now so payments generation can use them later
for row in invoices:
    row.setdefault("period", None)

# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

payments: list[dict] = []
pay_counter = 1


def new_payment_id() -> str:
    global pay_counter
    pid = f"PAY-{pay_counter:04d}"
    pay_counter += 1
    return pid


payable_invoices = [r for r in invoices if r["entity_code"]]  # can't pay an invoice with no entity
for row in payable_invoices:
    if random.random() < 0.75:  # most, not all, invoices are paid within the dataset window
        pay_date = date.fromisoformat(row["invoice_date"]) + timedelta(days=random.randint(5, 35))
        payments.append({
            "payment_id": new_payment_id(),
            "entity_code": row["entity_code"],
            "invoice_id": row["invoice_id"],
            "payment_date": pay_date.isoformat(),
            "currency": row["currency"],
            "amount": row["amount"],
            "payment_type": "received" if row["invoice_type"] == "AR" else "made",
            "source": "bank_csv",
            "status": "matched",
        })

# Duplicate payments: the same invoice paid twice
dup_payment_sources = random.sample(payments, 4)
for src in dup_payment_sources:
    dup = dict(src)
    dup["payment_id"] = new_payment_id()
    dup["payment_date"] = (date.fromisoformat(src["payment_date"]) + timedelta(days=random.randint(1, 5))).isoformat()
    payments.append(dup)
    log_issue("duplicate_payment", "payments", f"{src['payment_id']}, {dup['payment_id']}",
              f"invoice {src['invoice_id']} paid twice for the same amount")

# Missing invoice references: unapplied cash receipts with no invoice_id
for _ in range(5):
    entity_code = random.choice(ENTITY_CODES)
    period = random.choice(PERIODS)
    payments.append({
        "payment_id": new_payment_id(),
        "entity_code": entity_code,
        "invoice_id": "",
        "payment_date": random_date_in(period).isoformat(),
        "currency": ENTITY_CURRENCY[entity_code],
        "amount": round(random.uniform(500, 8000), 2),
        "payment_type": "received",
        "source": "bank_csv",
        "status": "unmatched",
    })
    log_issue("missing_invoice_reference", "payments", payments[-1]["payment_id"],
              "no invoice_id -- unapplied cash receipt")

# ---------------------------------------------------------------------------
# Bank transactions -- most reconcile to a payment, a deliberate minority don't
# ---------------------------------------------------------------------------

bank_transactions: list[dict] = []
bank_counter = 1
descriptions = ["FASTER PAYMENT RECEIVED", "BACS PAYMENT", "WIRE TRANSFER", "DIRECT DEBIT",
                "CARD SETTLEMENT", "STANDING ORDER", "CHEQUE DEPOSIT"]

for pay in payments:
    if pay["invoice_id"] == "" or random.random() < 0.85:
        will_match = random.random() < 0.8
        bank_transactions.append({
            "bank_transaction_id": f"BANK-{bank_counter:04d}",
            "entity_code": pay["entity_code"],
            "bank_account_code": f"{pay['entity_code']}-OPS",
            "transaction_date": (date.fromisoformat(pay["payment_date"]) + timedelta(days=random.randint(0, 2))).isoformat(),
            "currency": pay["currency"],
            "amount": pay["amount"],
            "description": random.choice(descriptions),
            "source": "bank_csv",
            "match_status": "matched" if will_match else "unmatched",
            "matched_payment_id": pay["payment_id"] if will_match else "",
        })
        bank_counter += 1
        if not will_match:
            log_issue("unmatched_bank_transaction", "bank_transactions", bank_transactions[-1]["bank_transaction_id"],
                      f"amount/timing mismatch against payment {pay['payment_id']} -- left unmatched")

# A handful of bank-only items with no corresponding payment at all (bank fees, interest)
for _ in range(10):
    entity_code = random.choice(ENTITY_CODES)
    period = random.choice(PERIODS)
    bank_transactions.append({
        "bank_transaction_id": f"BANK-{bank_counter:04d}",
        "entity_code": entity_code,
        "bank_account_code": f"{entity_code}-OPS",
        "transaction_date": random_date_in(period).isoformat(),
        "currency": ENTITY_CURRENCY[entity_code],
        "amount": round(random.uniform(-250, -5), 2),
        "description": "BANK CHARGES",
        "source": "bank_csv",
        "match_status": "unmatched",
        "matched_payment_id": "",
    })
    bank_counter += 1
    log_issue("unmatched_bank_transaction", "bank_transactions", bank_transactions[-1]["bank_transaction_id"],
               "bank charge with no corresponding payment record -- needs a manual journal")

# Missing entity codes on a few bank rows too
missing_entity_bank = random.sample(bank_transactions, 3)
for row in missing_entity_bank:
    row["entity_code"] = ""
    log_issue("missing_entity_code", "bank_transactions", row["bank_transaction_id"], "entity_code blank at source")

# ---------------------------------------------------------------------------
# Journal entries + lines -- always balanced (debit = credit is never
# violated, even in messy synthetic data -- see data-model.md)
# ---------------------------------------------------------------------------

PREPARERS = ["G.Lin", "T.Marsh", "R.Adeyemi"]
APPROVER = "D.Okafor"

journal_entries: list[dict] = []
journal_lines: list[dict] = []
je_counter = 1
jl_counter = 1

MANUAL_CLASSIFICATIONS = ["accrual", "prepayment_release", "intercompany", "fx_revaluation", "payroll_accrual"]


def add_journal(entity_code: str, entry_date: date, period: str, currency: str,
                 source: str, classification: str, lines: list[tuple[str, float, float]],
                 late: bool = False) -> str:
    global je_counter, jl_counter
    je_id = f"JE-{je_counter:04d}"
    je_counter += 1
    preparer = random.choice(PREPARERS)
    posted = random.random() < 0.8
    journal_entries.append({
        "journal_entry_id": je_id,
        "entity_code": entity_code,
        "entry_date": entry_date.isoformat(),
        "period": period,
        "currency": currency,
        "source": source,
        "classification": classification,
        "status": "posted" if posted else "pending_approval",
        "created_by": preparer,
        "approved_by": APPROVER if posted else "",
        "description": f"{classification.replace('_', ' ').title()} - {entity_code} {period}",
    })
    for account_code, debit, credit in lines:
        journal_lines.append({
            "journal_line_id": f"JL-{jl_counter:04d}",
            "journal_entry_id": je_id,
            "account_code": account_code,
            "debit_amount": debit,
            "credit_amount": credit,
            "line_description": f"{classification.replace('_', ' ').title()} line",
        })
        jl_counter += 1
    if late:
        log_issue("late_transaction", "journal_entries", je_id,
                  f"entry_date {entry_date.isoformat()} falls in an earlier month than "
                  f"period '{period}' -- posted late against the close it belongs to")
    return je_id


for period in PERIODS:
    for entity_code in ENTITY_CODES:
        currency = ENTITY_CURRENCY[entity_code]
        n_manual = random.randint(3, 5)
        n_system = random.randint(1, 2)  # ~70/30 manual/system split, matching discovery-notes.md

        for _ in range(n_manual):
            classification = random.choice(MANUAL_CLASSIFICATIONS)
            amount = round(random.uniform(500, 15000), 2)
            expense_acct = random.choice(EXPENSE_ACCOUNTS)
            entry_date = random_date_in(period)
            late = period == CURRENT_CLOSE_PERIOD and random.random() < 0.15
            if late:
                prev_start, prev_end = month_bounds(PERIODS[PERIODS.index(period) - 1])
                entry_date = prev_end - timedelta(days=random.randint(0, 3))
            add_journal(
                entity_code, entry_date, period, currency, "manual", classification,
                lines=[(expense_acct, amount, 0.0), ("2010", 0.0, amount)],
                late=late,
            )

        for _ in range(n_system):
            amount = round(random.uniform(1000, 20000), 2)
            entry_date = random_date_in(period)
            add_journal(
                entity_code, entry_date, period, currency, "system", "ar_ap_subledger",
                lines=[("1010" if random.random() < 0.5 else "2000", amount, 0.0),
                       ("4000" if random.random() < 0.5 else "5000", 0.0, amount)],
            )

# ---------------------------------------------------------------------------
# Intercompany transactions -- most reconcile between the two counterparties,
# a deliberate minority are left as exceptions (R04)
# ---------------------------------------------------------------------------

intercompany_transactions: list[dict] = []
ic_counter = 1

entity_pairs = [(a, b) for a in ENTITY_CODES for b in ENTITY_CODES if a != b]

for period in PERIODS:
    for _ in range(10):
        entity_from, entity_to = random.choice(entity_pairs)
        amount = round(random.uniform(1000, 30000), 2)
        currency = ENTITY_CURRENCY[entity_from]
        reference = f"IC-{period.replace('-', '')}-{random.randint(1000, 9999)}"
        txn_date = random_date_in(period)
        will_match = random.random() < 0.75

        intercompany_transactions.append({
            "intercompany_transaction_id": f"IC-{ic_counter:04d}",
            "entity_from_code": entity_from,
            "entity_to_code": entity_to,
            "transaction_date": txn_date.isoformat(),
            "currency": currency,
            "amount": amount,
            "reference": reference,
            "source": "intercompany_spreadsheet",
            "match_status": "matched" if will_match else "unmatched",
            "related_journal_entry_id": "",
        })
        ic_counter += 1

        if will_match:
            # counterpart entry from the other entity's side, same reference/amount
            intercompany_transactions.append({
                "intercompany_transaction_id": f"IC-{ic_counter:04d}",
                "entity_from_code": entity_to,
                "entity_to_code": entity_from,
                "transaction_date": (txn_date + timedelta(days=random.randint(0, 2))).isoformat(),
                "currency": currency,
                "amount": amount,
                "reference": reference,
                "source": "intercompany_spreadsheet",
                "match_status": "matched",
                "related_journal_entry_id": "",
            })
            ic_counter += 1
        else:
            log_issue("unmatched_intercompany_transaction", "intercompany_transactions",
                      intercompany_transactions[-1]["intercompany_transaction_id"],
                      f"no counterpart entry recorded on {entity_to}'s side for reference {reference} "
                      f"-- reference/timing mismatch, matches the ~35/month pattern in discovery-notes.md")

# ---------------------------------------------------------------------------
# Write CSVs
# ---------------------------------------------------------------------------

TABLES = {
    "entities.csv": ENTITIES,
    "chart_of_accounts.csv": CHART_OF_ACCOUNTS,
    "customers.csv": CUSTOMERS,
    "vendors.csv": VENDORS,
    "fx_rates.csv": fx_rates,
    "invoices.csv": invoices,
    "payments.csv": payments,
    "bank_transactions.csv": bank_transactions,
    "journal_entries.csv": journal_entries,
    "journal_lines.csv": journal_lines,
    "intercompany_transactions.csv": intercompany_transactions,
}

for filename, rows in TABLES.items():
    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR / filename, index=False)
    print(f"wrote {filename}: {len(df)} rows")

# ---------------------------------------------------------------------------
# Write the data-quality log (ground truth for later validation/reconciliation)
# ---------------------------------------------------------------------------

log_path = OUTPUT_DIR / "data-quality-log.md"
with open(log_path, "w") as f:
    f.write("# Data Quality Log — Planted Issues\n\n")
    f.write(
        "Generated by `generate_data.py` (seed = "
        f"{SEED}). Every row below is a data-quality issue deliberately "
        "injected into the synthetic CSVs in this folder, per PLAN.md §19. "
        "This is the ground truth Phase 9 (ingestion/validation) and Phase 13 "
        "(reconciliation) should be checked against -- if their detection "
        "logic doesn't find everything listed here, it isn't working.\n\n"
    )
    categories = sorted(set(i["category"] for i in issues))
    for cat in categories:
        cat_issues = [i for i in issues if i["category"] == cat]
        f.write(f"## {cat.replace('_', ' ').title()} ({len(cat_issues)})\n\n")
        f.write("| Table | ID(s) | Description |\n|---|---|---|\n")
        for i in cat_issues:
            f.write(f"| {i['table']} | {i['ids']} | {i['description']} |\n")
        f.write("\n")

print(f"wrote data-quality-log.md: {len(issues)} planted issues across {len(categories)} categories")
