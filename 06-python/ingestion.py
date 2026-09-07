"""Ingestion pipeline (Phase 9, PLAN.md §21).

    Source File -> Read -> Schema Validation -> Data Quality Checks ->
    Duplicate Detection -> Entity/Account Mapping -> Currency Normalisation
    -> Database Load -> Reconciliation -> Exception Report

Runs the raw CSVs in 04-data/ (invoices, payments, bank_transactions,
intercompany_transactions -- the four tables that come from an external
source, per system-architecture.md) through every stage above, reloads
them into the northstar database, and writes a fresh exception report.

This replaces 05-sql/seed.sql's plain-SQL load for these four tables with
something that can actually recover a couple more rows (fuzzy vendor-name
matching), flags duplicates as duplicate_flagged rather than dropping or
silently posting them, and independently re-derives bank/intercompany
matches instead of trusting the source data's own match_status label.

Run from the repo root: .venv/bin/python 06-python/ingestion.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from db import get_engine
from mappings import load_reference_data, map_account, map_customer, map_entity, map_vendor
from reconciliation import flag_duplicate_invoices, match_intercompany, match_transactions
from transformations import build_rate_table, to_reporting_currency
from validation import BankTransactionRow, IntercompanyRow, InvoiceRow, PaymentRow, validate_rows

DATA_DIR = Path(__file__).resolve().parent.parent / "04-data"
REPORT_PATH = Path(__file__).resolve().parent / "exception-report.md"


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name, dtype=str, keep_default_na=True)


def run() -> None:
    engine = get_engine()
    exceptions: list[dict] = []

    def log(category: str, table: str, id_hint, detail: str) -> None:
        exceptions.append({"category": category, "table": table, "id": id_hint, "detail": detail})

    print("Loading reference data (entities, customers, vendors, accounts)...")
    ref = load_reference_data(engine)
    fx_rates = build_rate_table(pd.read_sql("SELECT * FROM fx_rates", engine))

    # -----------------------------------------------------------------
    # Invoices: read -> validate -> map -> currency-normalise -> dup-flag
    # -----------------------------------------------------------------
    print("Processing invoices...")
    raw_invoices = read_csv("invoices.csv")
    valid_invoices, invoice_val_errors = validate_rows(raw_invoices, InvoiceRow)
    for err in invoice_val_errors:
        log("schema_validation_failed", "invoices", err["id_hint"], str(err["errors"]))

    inv_df = pd.DataFrame(valid_invoices)
    inv_df["entity_id"] = inv_df["entity_code"].apply(lambda c: map_entity(c, ref))
    inv_df["customer_id"] = inv_df["customer_code"].apply(lambda c: map_customer(c, ref))
    inv_df["account_id"] = inv_df["account_code"].apply(lambda c: map_account(c, ref))

    vendor_results = inv_df.apply(
        lambda r: map_vendor(r["vendor_code"], r["vendor_name_raw"], ref), axis=1
    )
    inv_df["vendor_id"] = vendor_results.apply(lambda t: t[0])
    inv_df["vendor_match_method"] = vendor_results.apply(lambda t: t[1])

    for _, row in inv_df.iterrows():
        # NOTE: pandas silently turns a Python None into a float NaN in a
        # mixed-type column (see mappings.py's _blank() for the same issue),
        # so these checks use pd.isna(), never `is None`.
        if pd.isna(row["entity_id"]):
            log("missing_entity_code", "invoices", row["invoice_id"], "entity_code did not resolve")
        if row["invoice_type"] == "AR" and pd.isna(row["customer_id"]):
            log("unresolved_customer", "invoices", row["invoice_id"], f"customer_code {row['customer_code']!r} did not resolve")
        if row["invoice_type"] == "AP" and pd.isna(row["vendor_id"]):
            log("unresolved_vendor", "invoices", row["invoice_id"],
                f"neither vendor_code nor vendor_name_raw {row['vendor_name_raw']!r} resolved")
        elif row["vendor_match_method"] == "fuzzy_name":
            log("vendor_resolved_by_fuzzy_match", "invoices", row["invoice_id"],
                f"vendor_name_raw {row['vendor_name_raw']!r} matched by fuzzy name (recovered vs. seed.sql)")

    loadable_mask = inv_df["entity_id"].notna() & (
        ((inv_df["invoice_type"] == "AR") & inv_df["customer_id"].notna())
        | ((inv_df["invoice_type"] == "AP") & inv_df["vendor_id"].notna())
    )
    inv_loadable = inv_df[loadable_mask].copy()
    inv_loadable = flag_duplicate_invoices(inv_loadable)

    dup_rows = inv_loadable[inv_loadable["duplicate_of"].notna()]
    for _, row in dup_rows.iterrows():
        log("duplicate_invoice_flagged", "invoices", row["invoice_id"],
            f"duplicate of {row['duplicate_of']} on (entity, invoice_number, invoice_type)")

    converted = inv_loadable.apply(
        lambda r: to_reporting_currency(r["amount"], r["currency"], r["invoice_date"], fx_rates), axis=1
    )
    inv_loadable["amount_gbp"] = converted.apply(lambda t: t[0])
    for _, row in inv_loadable[inv_loadable["amount_gbp"].isna()].iterrows():
        log("currency_conversion_failed", "invoices", row["invoice_id"], f"no fx rate available for {row['currency']}")

    invoices_final = inv_loadable[[
        "invoice_id", "invoice_type", "invoice_number", "entity_id", "customer_id", "vendor_id",
        "invoice_date", "due_date", "currency", "amount", "source", "account_id", "status",
    ]].copy()

    # -----------------------------------------------------------------
    # Payments
    # -----------------------------------------------------------------
    print("Processing payments...")
    raw_payments = read_csv("payments.csv")
    valid_payments, payment_val_errors = validate_rows(raw_payments, PaymentRow)
    for err in payment_val_errors:
        log("schema_validation_failed", "payments", err["id_hint"], str(err["errors"]))

    pay_df = pd.DataFrame(valid_payments)
    pay_df["entity_id"] = pay_df["entity_code"].apply(lambda c: map_entity(c, ref))
    loaded_invoice_ids = set(invoices_final["invoice_id"])
    pay_df["invoice_id"] = pay_df["invoice_id"].apply(lambda i: i if i in loaded_invoice_ids else None)

    for _, row in pay_df.iterrows():
        if pd.isna(row["entity_id"]):
            log("missing_entity_code", "payments", row["payment_id"], "entity_code did not resolve")

    payments_final = pay_df[pay_df["entity_id"].notna()][[
        "payment_id", "entity_id", "invoice_id", "payment_date", "currency", "amount",
        "payment_type", "source", "status",
    ]].copy()

    # -----------------------------------------------------------------
    # Bank transactions -- independently re-matched against payments,
    # rather than trusting the source's own match_status/matched_payment_id
    # -----------------------------------------------------------------
    print("Processing bank transactions...")
    raw_bank = read_csv("bank_transactions.csv")
    valid_bank, bank_val_errors = validate_rows(raw_bank, BankTransactionRow)
    for err in bank_val_errors:
        log("schema_validation_failed", "bank_transactions", err["id_hint"], str(err["errors"]))

    bank_df = pd.DataFrame(valid_bank)
    bank_df["entity_id"] = bank_df["entity_code"].apply(lambda c: map_entity(c, ref))
    for _, row in bank_df[bank_df["entity_id"].isna()].iterrows():
        log("missing_entity_code", "bank_transactions", row["bank_transaction_id"], "entity_code did not resolve")
    bank_loadable = bank_df[bank_df["entity_id"].notna()].copy()

    matches, unmatched_bank = match_transactions(bank_loadable, payments_final)
    matched_ids = dict(zip(matches["bank_transaction_id"], matches["payment_id"]))
    bank_loadable["match_status"] = bank_loadable["bank_transaction_id"].apply(
        lambda i: "matched" if i in matched_ids else "unmatched"
    )
    bank_loadable["matched_payment_id"] = bank_loadable["bank_transaction_id"].map(matched_ids)

    for _, row in bank_loadable[bank_loadable["match_status"] == "unmatched"].iterrows():
        log("unmatched_bank_transaction", "bank_transactions", row["bank_transaction_id"],
            "no payment found within amount/date tolerance")

    bank_final = bank_loadable[[
        "bank_transaction_id", "entity_id", "bank_account_code", "transaction_date", "currency",
        "amount", "description", "source", "match_status", "matched_payment_id",
    ]].copy()

    # -----------------------------------------------------------------
    # Intercompany transactions -- independently re-matched by reference
    # -----------------------------------------------------------------
    print("Processing intercompany transactions...")
    raw_ic = read_csv("intercompany_transactions.csv")
    valid_ic, ic_val_errors = validate_rows(raw_ic, IntercompanyRow)
    for err in ic_val_errors:
        log("schema_validation_failed", "intercompany_transactions", err["id_hint"], str(err["errors"]))

    ic_df = pd.DataFrame(valid_ic)
    ic_df["entity_from_id"] = ic_df["entity_from_code"].apply(lambda c: map_entity(c, ref))
    ic_df["entity_to_id"] = ic_df["entity_to_code"].apply(lambda c: map_entity(c, ref))
    ic_loadable = ic_df[ic_df["entity_from_id"].notna() & ic_df["entity_to_id"].notna()].copy()

    matched_ic, unmatched_ic = match_intercompany(ic_loadable)
    ic_loadable["match_status"] = ic_loadable["intercompany_transaction_id"].apply(
        lambda i: "matched" if i in set(matched_ic["intercompany_transaction_id"]) else "unmatched"
    )
    for _, row in ic_loadable[ic_loadable["match_status"] == "unmatched"].iterrows():
        log("unmatched_intercompany_transaction", "intercompany_transactions", row["intercompany_transaction_id"],
            f"reference {row['reference']} has no matching counterpart within tolerance")

    ic_final = ic_loadable[[
        "intercompany_transaction_id", "entity_from_id", "entity_to_id", "transaction_date", "currency",
        "amount", "reference", "source", "match_status", "related_journal_entry_id",
    ]].copy()

    # -----------------------------------------------------------------
    # Database load -- replaces these four tables' contents with the
    # pipeline's output. FK order: bank_transactions/payments before
    # invoices on the way out, invoices before payments/bank on the way in.
    # -----------------------------------------------------------------
    print("Loading into the database...")
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "TRUNCATE TABLE bank_transactions, payments, invoices, intercompany_transactions"
        )
        invoices_final.to_sql("invoices", conn, if_exists="append", index=False)
        payments_final.to_sql("payments", conn, if_exists="append", index=False)
        bank_final.to_sql("bank_transactions", conn, if_exists="append", index=False)
        ic_final.to_sql("intercompany_transactions", conn, if_exists="append", index=False)

    print(f"  invoices: {len(invoices_final)} loaded ({len(raw_invoices) - len(invoices_final)} excluded)")
    print(f"  payments: {len(payments_final)} loaded")
    print(f"  bank_transactions: {len(bank_final)} loaded")
    print(f"  intercompany_transactions: {len(ic_final)} loaded")

    write_report(exceptions, len(raw_invoices), len(invoices_final))


def write_report(exceptions: list[dict], invoices_read: int, invoices_loaded: int) -> None:
    categories = sorted({e["category"] for e in exceptions})
    with open(REPORT_PATH, "w") as f:
        f.write("# Exception Report — Phase 9 Ingestion Run\n\n")
        f.write(
            f"Generated by `ingestion.py`. Read {invoices_read} raw invoices, "
            f"loaded {invoices_loaded} into the database "
            f"({invoices_read - invoices_loaded} excluded). "
            f"{len(exceptions)} total exceptions across {len(categories)} categories.\n\n"
        )
        for cat in categories:
            cat_exceptions = [e for e in exceptions if e["category"] == cat]
            f.write(f"## {cat.replace('_', ' ').title()} ({len(cat_exceptions)})\n\n")
            f.write("| Table | ID | Detail |\n|---|---|---|\n")
            for e in cat_exceptions:
                f.write(f"| {e['table']} | {e['id']} | {e['detail']} |\n")
            f.write("\n")
    print(f"Wrote {REPORT_PATH} ({len(exceptions)} exceptions)")


if __name__ == "__main__":
    run()
