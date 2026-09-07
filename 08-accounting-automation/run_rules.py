"""Runs every Phase 11 rule against the real northstar database and writes
rule-findings.md -- the same "prove it against real data, not just unit
tests" pattern as every prior phase (data-quality-log.md,
exception-report.md).

Run from the repo root: .venv/bin/python 08-accounting-automation/run_rules.py
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from db import get_engine
from exception_rules import Exception_, check_duplicate_invoices, check_intercompany_counterpart, check_required_fields
from invoice_classification import classify_vendor_account, requires_fx_conversion, validate_entity_ledger
from journal_workflow import determine_journal_status

REPORT_PATH = Path(__file__).resolve().parent / "rule-findings.md"


def run() -> None:
    engine = get_engine()
    findings: list[Exception_] = []

    with engine.connect() as conn:
        invoices = [dict(row) for row in conn.execute(text("""
            SELECT invoice_id, entity_id, invoice_number, invoice_type, customer_id, vendor_id,
                   invoice_date, currency, amount, status, account_id
            FROM invoices
        """)).mappings().all()]

        vendor_defaults = dict(conn.execute(text(
            "SELECT vendor_id, default_account_id FROM vendors"
        )).all())

        entity_currency = dict(conn.execute(text(
            "SELECT entity_id, functional_currency FROM entities"
        )).all())

        intercompany = [dict(row) for row in conn.execute(text("""
            SELECT intercompany_transaction_id, reference, amount FROM intercompany_transactions
        """)).mappings().all()]

        intercompany_fx = [dict(row) for row in conn.execute(text("""
            SELECT ic.intercompany_transaction_id, ic.currency, et.functional_currency AS to_entity_currency
            FROM intercompany_transactions ic
            JOIN entities et ON et.entity_id = ic.entity_to_id
        """)).mappings().all()]

        journal_entries = [dict(row) for row in conn.execute(text("""
            SELECT je.journal_entry_id, je.created_by, je.approved_by, je.status,
                   COALESCE(SUM(jl.debit_amount), 0) AS amount
            FROM journal_entries je
            JOIN journal_lines jl ON jl.journal_entry_id = je.journal_entry_id
            GROUP BY je.journal_entry_id, je.created_by, je.approved_by, je.status
        """)).mappings().all()]

    # --- exception_rules.py -------------------------------------------------
    findings += check_duplicate_invoices(invoices)
    for inv in invoices:
        findings += check_required_fields(inv)
    findings += check_intercompany_counterpart(intercompany)

    # --- invoice_classification.py ------------------------------------------
    for inv in invoices:
        if inv["invoice_type"] == "AP":
            result = classify_vendor_account(vendor_defaults.get(inv["vendor_id"]), inv["account_id"])
            if result.exception:
                findings.append(Exception_(rule="incorrect_account_mapping", id=inv["invoice_id"], detail=result.exception))

        ledger_issue = validate_entity_ledger(inv["entity_id"])
        if ledger_issue:
            findings.append(Exception_(rule="no_ledger", id=inv["invoice_id"], detail=ledger_issue))

        entity_ccy = entity_currency.get(inv["entity_id"])
        if entity_ccy and requires_fx_conversion(inv["currency"], entity_ccy):
            findings.append(Exception_(
                rule="fx_conversion_required", id=inv["invoice_id"],
                detail=f"invoice currency {inv['currency']} differs from entity functional currency {entity_ccy}",
            ))

    # invoices never actually cross a currency boundary in this synthetic
    # dataset (every invoice is billed in its own entity's functional
    # currency by construction -- see 04-data/generate_data.py), so the
    # rule above never fires on real data. Intercompany transactions do
    # cross currency boundaries (entity_from bills in its own currency,
    # entity_to may use a different one), which is where this rule
    # actually has something to catch:
    for row in intercompany_fx:
        if requires_fx_conversion(row["currency"], row["to_entity_currency"]):
            findings.append(Exception_(
                rule="fx_conversion_required", id=row["intercompany_transaction_id"],
                detail=f"transaction currency {row['currency']} differs from receiving entity's "
                       f"functional currency {row['to_entity_currency']}",
            ))

    # --- journal_workflow.py -------------------------------------------------
    workflow_mismatches = 0
    for je in journal_entries:
        rule_result = determine_journal_status(float(je["amount"]), je["created_by"], je["approved_by"])
        if rule_result.status == "pending_approval" and je["status"] == "posted":
            workflow_mismatches += 1
            findings.append(Exception_(
                rule="posted_without_required_approval", id=je["journal_entry_id"],
                detail=f"amount {je['amount']} required approval per the {rule_result.reason}, "
                       f"but the entry is already posted",
            ))

    write_report(findings, len(invoices), len(journal_entries), workflow_mismatches)


def write_report(findings: list[Exception_], invoice_count: int, journal_count: int, workflow_mismatches: int) -> None:
    categories = sorted({f.rule for f in findings})
    with open(REPORT_PATH, "w") as f:
        f.write("# Rule Findings — Phase 11 Accounting Automation\n\n")
        f.write(
            f"Generated by `run_rules.py` against the real `northstar` database. "
            f"Checked {invoice_count} invoices and {journal_count} journal entries. "
            f"{len(findings)} total findings across {len(categories)} rules "
            f"({workflow_mismatches} of which are posted journal entries that should have required approval).\n\n"
        )
        for cat in categories:
            cat_findings = [x for x in findings if x.rule == cat]
            f.write(f"## {cat.replace('_', ' ').title()} ({len(cat_findings)})\n\n")
            f.write("| ID | Detail |\n|---|---|\n")
            for x in cat_findings:
                f.write(f"| {x.id} | {x.detail} |\n")
            f.write("\n")
    print(f"wrote {REPORT_PATH} ({len(findings)} findings across {len(categories)} rules)")


if __name__ == "__main__":
    run()
