# Sample extracts — the raw, pre-ingestion data

First 8 rows of each source file, exactly as they arrive at the ingestion pipeline ([`04-data/`](../../04-data/)). All data is **synthetic** — generated deterministically (seed 42) by [`generate_data.py`](../../04-data/generate_data.py); no real client, customer, or vendor data is used anywhere in this repo.

Blank cells are real: they are the planted data-quality problems (e.g. `INV-0004` has no `entity_code`). The full ground-truth list of what was planted is in [seeded-issues-vs-detected.md](./seeded-issues-vs-detected.md).

## `invoices.csv` — Billing (AR) and AP invoices, raw pre-mapping form

92 rows total. Source: [`04-data/invoices.csv`](../../04-data/invoices.csv)

| invoice_id | invoice_type | invoice_number | entity_code | customer_code | vendor_code | vendor_name_raw | invoice_date | due_date | currency | amount | source | account_code | status | period |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| INV-0001 | AR | NSS-UK-AR-202606-C0001 | NSS-UK | C0001 | *(blank)* | *(blank)* | 2026-06-05 | 2026-07-05 | GBP | 11258.49 | billing_api | 4020 | open | 2026-06 |
| INV-0002 | AR | NHH-UK-AR-202606-C0002 | NHH-UK | C0002 | *(blank)* | *(blank)* | 2026-06-13 | 2026-07-13 | GBP | 6158.8 | billing_api | 4020 | open | 2026-06 |
| INV-0003 | AR | NHH-UK-AR-202606-C0003 | NHH-UK | C0003 | *(blank)* | *(blank)* | 2026-06-26 | 2026-07-26 | GBP | 3868.37 | billing_api | 4030 | open | 2026-06 |
| INV-0004 | AR | NSS-UK-AR-202606-C0004 | *(blank)* | C0004 | *(blank)* | *(blank)* | 2026-06-30 | 2026-07-30 | GBP | 18276.98 | billing_api | 4020 | open | 2026-06 |
| INV-0005 | AR | NHS-US-AR-202606-C0005 | NHS-US | C0005 | *(blank)* | *(blank)* | 2026-06-20 | 2026-07-20 | USD | 40074.43 | billing_api | 4020 | open | 2026-06 |
| INV-0006 | AR | NHH-UK-AR-202606-C0006 | NHH-UK | C0006 | *(blank)* | *(blank)* | 2026-06-23 | 2026-07-23 | GBP | 4990.87 | billing_api | 4010 | open | 2026-06 |
| INV-0007 | AR | NHH-UK-AR-202606-C0007 | NHH-UK | C0007 | *(blank)* | *(blank)* | 2026-06-03 | 2026-07-03 | GBP | 38778.66 | billing_api | 4000 | open | 2026-06 |
| INV-0008 | AR | NHH-UK-AR-202606-C0008 | NHH-UK | C0008 | *(blank)* | *(blank)* | 2026-06-15 | 2026-07-15 | GBP | 29334.43 | billing_api | 4020 | open | 2026-06 |

## `payments.csv` — Payments against invoices

76 rows total. Source: [`04-data/payments.csv`](../../04-data/payments.csv)

| payment_id | entity_code | invoice_id | payment_date | currency | amount | payment_type | source | status |
|---|---|---|---|---|---|---|---|---|
| PAY-0001 | NHH-UK | INV-0002 | 2026-06-26 | GBP | 6158.8 | received | bank_csv | matched |
| PAY-0002 | NHH-UK | INV-0003 | 2026-07-31 | GBP | 3868.37 | received | bank_csv | matched |
| PAY-0003 | NHH-UK | INV-0006 | 2026-07-17 | GBP | 4990.87 | received | bank_csv | matched |
| PAY-0004 | NHH-UK | INV-0007 | 2026-07-01 | GBP | 38778.66 | received | bank_csv | matched |
| PAY-0005 | NSS-UK | INV-0009 | 2026-07-03 | GBP | 11008.8 | received | bank_csv | matched |
| PAY-0006 | NHH-UK | INV-0010 | 2026-07-25 | GBP | 29865.52 | received | bank_csv | matched |
| PAY-0007 | NSS-UK | INV-0011 | 2026-06-21 | GBP | 9026.31 | received | bank_csv | matched |
| PAY-0008 | NSS-UK | INV-0012 | 2026-07-18 | GBP | 29519.99 | received | bank_csv | matched |

## `bank_transactions.csv` — Bank statement lines

81 rows total. Source: [`04-data/bank_transactions.csv`](../../04-data/bank_transactions.csv)

| bank_transaction_id | entity_code | bank_account_code | transaction_date | currency | amount | description | source | match_status | matched_payment_id |
|---|---|---|---|---|---|---|---|---|---|
| BANK-0001 | NHH-UK | NHH-UK-OPS | 2026-06-27 | GBP | 6158.8 | CARD SETTLEMENT | bank_csv | matched | PAY-0001 |
| BANK-0002 | NHH-UK | NHH-UK-OPS | 2026-08-02 | GBP | 3868.37 | DIRECT DEBIT | bank_csv | matched | PAY-0002 |
| BANK-0003 | NHH-UK | NHH-UK-OPS | 2026-07-17 | GBP | 4990.87 | WIRE TRANSFER | bank_csv | matched | PAY-0003 |
| BANK-0004 | NHH-UK | NHH-UK-OPS | 2026-07-02 | GBP | 38778.66 | WIRE TRANSFER | bank_csv | matched | PAY-0004 |
| BANK-0005 | NSS-UK | NSS-UK-OPS | 2026-07-04 | GBP | 11008.8 | WIRE TRANSFER | bank_csv | matched | PAY-0005 |
| BANK-0006 | NHH-UK | NHH-UK-OPS | 2026-07-27 | GBP | 29865.52 | CARD SETTLEMENT | bank_csv | matched | PAY-0006 |
| BANK-0007 | NSS-UK | NSS-UK-OPS | 2026-06-21 | GBP | 9026.31 | STANDING ORDER | bank_csv | unmatched | *(blank)* |
| BANK-0008 | NSS-UK | NSS-UK-OPS | 2026-07-18 | GBP | 29519.99 | CHEQUE DEPOSIT | bank_csv | unmatched | *(blank)* |

## `intercompany_transactions.csv` — Entity-to-entity transactions

48 rows total. Source: [`04-data/intercompany_transactions.csv`](../../04-data/intercompany_transactions.csv)

| intercompany_transaction_id | entity_from_code | entity_to_code | transaction_date | currency | amount | reference | source | match_status | related_journal_entry_id |
|---|---|---|---|---|---|---|---|---|---|
| IC-0001 | NHH-UK | NSS-UK | 2026-06-03 | GBP | 29078.0 | IC-202606-8450 | intercompany_spreadsheet | matched | *(blank)* |
| IC-0002 | NSS-UK | NHH-UK | 2026-06-05 | GBP | 29078.0 | IC-202606-8450 | intercompany_spreadsheet | matched | *(blank)* |
| IC-0003 | NSS-UK | NHS-US | 2026-06-02 | GBP | 18317.23 | IC-202606-1349 | intercompany_spreadsheet | unmatched | *(blank)* |
| IC-0004 | NHH-UK | NSS-UK | 2026-06-03 | GBP | 29675.81 | IC-202606-4362 | intercompany_spreadsheet | unmatched | *(blank)* |
| IC-0005 | NSS-UK | NHH-UK | 2026-06-27 | GBP | 7007.56 | IC-202606-4538 | intercompany_spreadsheet | unmatched | *(blank)* |
| IC-0006 | NHS-US | NHH-UK | 2026-06-09 | USD | 23456.69 | IC-202606-1046 | intercompany_spreadsheet | unmatched | *(blank)* |
| IC-0007 | NHH-UK | NSS-UK | 2026-06-09 | GBP | 29638.29 | IC-202606-9850 | intercompany_spreadsheet | unmatched | *(blank)* |
| IC-0008 | NHH-UK | NHS-US | 2026-06-05 | GBP | 20170.67 | IC-202606-1422 | intercompany_spreadsheet | matched | *(blank)* |
