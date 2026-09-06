# Discovery Notes — Northstar Health Group

*Simulated notes from discovery conversations against the [discovery-script.md](./discovery-script.md), for this fictional portfolio POC. Written as consolidated notes rather than a verbatim transcript. Baseline metrics referenced here match the fictional current-state profile in PLAN.md §5.*

## Session participants (fictional)
- Sarah Whitfield, Group CFO
- David Okafor, Group Financial Controller
- Grace Lin, Shared Services Manager

## Business

- Month-end close currently takes **~12 business days**. The first week is largely consumed by data collection and reconciliation; the second week is journal review, intercompany resolution, and reporting assembly.
- Most manual/time-consuming steps: bank reconciliation, intercompany matching, and manual journal preparation for revenue and accruals.
- Exceptions cluster around intercompany transactions between the two UK entities and the US entity, largely due to FX timing and mismatched references.
- The team's biggest frustration is re-doing reconciliation work each month because source data changes late (e.g. a corrected invoice re-issued after initial import).
- The board wants a monthly P&L by entity, cash position, and an intercompany elimination summary — currently assembled by hand in PowerPoint from several Excel workbooks.

## Accounting

- Journal entries are prepared in Excel templates, then keyed into the legacy ERP by the Shared Services team. Roughly **70% of journals are manual** (accruals, prepayments, intercompany, FX revaluation); the rest are system-generated from AP/AR subledgers.
- Bank reconciliations are performed monthly in Excel against bank CSV exports — matching is largely manual, with **~80% of reconciling items resolved by hand**.
- Intercompany balances are tracked in a shared spreadsheet and matched manually between entity controllers; unresolved items are carried forward and average **~35 exceptions per month**.
- Journal approval is via email sign-off or a hard-copy sign sheet — there's no single system of record for who approved what.
- FX: USD transactions are converted at month-end spot rate in Excel; there's no consistent, auditable rate source across entities.

## Systems

- Each entity's legacy ERP install is not consistently configured — chart of accounts differs slightly by entity, which complicates consolidation.
- The billing platform is separate from the ERP; billing data is exported and **manually re-entered (100% manual)** into the ERP.
- Bank connectivity is CSV export from online banking, downloaded manually by the Shared Services team.
- AP invoices arrive by email as PDFs and are entered manually; there is no OCR or invoice-capture tooling in place.
- No single system is treated as the definitive source of truth for customers, vendors, or chart of accounts — each entity maintains its own local lists with informal reconciliation.

## Data

- Data arrives as CSV (bank), PDF (AP invoices), and manual export (billing) — no APIs are currently used.
- Bank and billing data are pulled monthly; AP invoices arrive continuously through the month.
- Identifiers are inconsistent: invoice numbers are sometimes reused across entities, and vendor names are entered freehand (e.g. "Med Supplies Ltd" vs "Medical Supplies Limited").
- Duplicate invoices are a known, recurring issue, generally caught only during payment run review.
- Entity and account mapping between the billing platform and the ERP is maintained in an unofficial Excel lookup table, owned informally by one team member.

## Controls

- Any Shared Services team member with ERP access can create a journal entry; there's no enforced maker/checker distinction in the system itself — it's a manual sign-off convention.
- There's an informal approval threshold (journals over a certain value require Controller sign-off) but it isn't systematically enforced.
- Evidence of approval is inconsistent — sometimes an email thread, sometimes a printed sign-off sheet, sometimes nothing beyond verbal agreement.
- Changes to posted entries are possible directly in the legacy ERP with no system-enforced audit trail; the team relies on manual change logs kept in Excel.

## Reporting

- The CFO wants a same-day view of group cash position and any large intercompany movements — not currently possible without asking Shared Services to manually check.
- During close, the Controller needs day-by-day visibility into which reconciliations and journals are outstanding — currently tracked in a shared Excel close checklist.
- Management reporting (P&L by entity, board pack) takes **~2 days** to assemble by hand from multiple Excel exports.

## Technology

- No integrations currently exist between billing, banking, and the ERP.
- The billing platform is believed to have an API, but it has never been used by finance or IT.
- If systems changed, migration would need to cover: chart of accounts, customer/vendor master data, open AP/AR balances, and at least 12 months of transaction history for trend reporting.
- Data security requirements are informal; there is no documented role-based access model for finance systems today.

## Synthesis

These notes directly informed the prioritised problem statement in [discovery-script.md](./discovery-script.md) and the requirements table in [requirements.md](./requirements.md). The recurring theme: **manual data movement and manual matching, not lack of accounting knowledge, is the core constraint** — which shapes the target architecture (PLAN.md §17) toward automated ingestion, validation, and reconciliation with human approval retained at decision points, not removed.
