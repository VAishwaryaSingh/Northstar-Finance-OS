# Current-State Process — Northstar Health Group

Based on [discovery-notes.md](../01-discovery/discovery-notes.md).

```text
Billing System
      ↓
CSV / Manual Export
      ↓
Excel
      ↓
Legacy ERP
      ↓
Finance Team
      ↓
Manual Reconciliation
      ↓
Manual Journals
      ↓
Intercompany Matching
      ↓
Reporting Workbook
      ↓
PowerPoint
      ↓
CFO
```

## Step-by-step detail

| Step | Process owner | System | Input | Output | Manual? | Control | Failure mode | Data-quality issue | Est. effort |
|---|---|---|---|---|---|---|---|---|---|
| Billing export | Shared Services | Billing platform | Billing period data | CSV/manual export | Yes | None systematic | Export missed or run twice | Duplicate rows | 0.5 day |
| Re-key into ERP | Shared Services | Excel → legacy ERP | Billing export | ERP transactions | Yes (100%) | Informal spot-check | Transcription error | Mismatched entity/account codes | 2 days |
| Bank reconciliation | Shared Services | Excel + bank CSV | Bank export, ERP cash ledger | Reconciled cash balance | Yes (~80%) | Manual sign-off | Missed/late items | Unmatched transactions | 2 days |
| Journal preparation | Controllers | Excel templates | Subledger + manual adjustments | Journal entries | Yes (~70%) | Email/paper sign-off | No enforced maker/checker | Journals posted without full support | 2 days |
| Intercompany matching | Entity controllers | Shared spreadsheet | Entity ledgers | Matched/unmatched IC balances | Yes | Manual review | Reference/timing mismatch | ~35 unresolved exceptions/month | 1.5 days |
| Reporting assembly | Group Controller | Excel exports | Ledger extracts | Reporting workbook | Yes | None systematic | Version drift across workbooks | Manual copy/paste errors | 1 day |
| Board pack | CFO / Controller | PowerPoint | Reporting workbook | Board pack | Yes | CFO review | Late/inconsistent numbers | Numbers not traceable to source | 1 day |

**Total close duration: ~12 business days.**

## Root pattern

Every handoff between systems (billing → Excel → ERP → Excel → PowerPoint) is manual and unvalidated at the point of transfer. Data-quality problems (duplicates, mismatched codes, unmatched intercompany items) are discovered downstream during reconciliation rather than caught at entry — this is the structural reason close takes 12 days and why ~80% of reconciliation work is manual. See [process-analysis.md](./process-analysis.md) for root-cause detail and [future-state.md](./future-state.md) for the target design.
