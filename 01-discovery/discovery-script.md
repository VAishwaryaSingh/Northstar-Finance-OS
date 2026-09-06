# Discovery Script — Northstar Health Group

*Fictional client discovery conversation, simulated for this portfolio POC. Structured as a first customer-discovery session with the CFO / Group Controller (see [stakeholder-map.md](./stakeholder-map.md)).*

## Purpose

Understand Northstar's current finance operating model well enough to (a) map current-state process, (b) design target-state process and architecture, and (c) derive prioritised requirements. Questions are grouped by theme; not every question is asked of every stakeholder — see stakeholder-map.md for who owns which detail.

## Business

- How long does month-end close currently take, start to finish?
- Which steps in close are most manual or time-consuming?
- Where do exceptions or errors most often occur?
- Which parts of the process cause the most frustration for the team?
- Which reports matter most to the board / leadership, and how are they currently produced?

## Accounting

- How are journal entries prepared today — manually in Excel, templated, or system-generated?
- How are bank and balance-sheet reconciliations performed?
- How are intercompany balances matched and settled between the three entities?
- Who approves journals, and how is that approval evidenced?
- How are multi-currency (GBP/USD) transactions recorded and revalued?

## Systems

- What ERP(s) are currently in use, and are they consistent across entities?
- What billing system(s) feed accounting data, and how?
- How do bank feeds reach the finance team — file download, portal, API?
- How are AP invoices received (email, portal, paper) and entered?
- Where do spreadsheets sit in the process, and why?
- Which system, if any, is considered the source of truth for each data type (customers, vendors, chart of accounts)?

## Data

- What formats does data arrive in (CSV, PDF, email, API)?
- How frequently is data updated — daily, weekly, on demand?
- What identifiers exist to match records across systems (invoice number, reference, vendor ID)?
- Are duplicate records a known issue, and where?
- How are entities and accounts mapped between source systems and the ledger?

## Controls

- Who has the ability to create a journal entry?
- Who approves journals, and are there approval thresholds by amount?
- What evidence is retained to support a journal or reconciliation (attachments, sign-off, audit log)?
- How are changes to posted entries tracked or restricted?

## Reporting

- What does the CFO need to see daily or weekly?
- What does the Controller need during the close cycle specifically?
- Which reports are still manually assembled (e.g. in Excel or PowerPoint), and by whom?

## Technology

- What integrations exist today between systems (if any)?
- Are APIs available from the billing system, bank, or ERP?
- What data would need to be migrated if the ERP or ledger changed?
- What security or access requirements apply to finance data?
- Are there existing role-based access controls, and how granular are they?

## Output of this session

Answers are captured in [discovery-notes.md](./discovery-notes.md) and synthesised into a prioritised problem statement below, which feeds [requirements.md](./requirements.md).

## Prioritised problem statement (draft, post-discovery)

1. **Close takes too long (12 business days)** because reconciliations and journal preparation are manual and sequential rather than parallel or automated.
2. **Reconciliations are spreadsheet-driven (~80% manual)**, making them slow, error-prone, and hard to evidence for audit.
3. **Billing data enters the ERP by manual re-keying**, creating delay and transcription risk between the billing system and the ledger.
4. **Intercompany transactions frequently fail to match (~35 exceptions/month)** across the three entities, consuming disproportionate close time relative to transaction volume.
5. **Management reporting is manually assembled (~2 days)** in Excel and PowerPoint, pulling from multiple disconnected sources.
6. **Data-quality issues (duplicates, missing entity codes, incorrect mappings) are found late** — usually during reconciliation rather than at point of entry.
7. **Multi-entity, multi-currency accounting adds structural complexity** that the current manual process was not designed to absorb at scale.
8. **There is real concern about control and auditability** if further automation is introduced without human oversight — this must be addressed by design, not retrofitted.

This statement is the direct input to [requirements.md](./requirements.md).
