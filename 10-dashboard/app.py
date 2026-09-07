"""Close Control Centre — Northstar Finance OS (Phase 14, PLAN.md §27).

A thin rendering layer over data.py's metric functions -- every number
shown here comes from a plain, independently-runnable, independently-
tested query or rule, never computed only here. Run:

    .venv/bin/streamlit run 10-dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from data import REFERENCE_DATE, get_all_metrics
from db import get_engine

st.set_page_config(page_title="Northstar Close Control Centre", layout="wide")

st.title("Northstar Finance OS — Close Control Centre")
st.caption(
    f"Fictional portfolio data for Northstar Health Group. Reference date used for overdue "
    f"calculations: {REFERENCE_DATE}. Every metric below is a live query or rule against the "
    f"real database (see 10-dashboard/data.py) — nothing here is a static snapshot."
)

engine = get_engine()
with engine.connect() as conn:
    metrics = get_all_metrics(conn)

close_progress = metrics["close_progress"]
outstanding = metrics["outstanding_reconciliations"]
unreconciled_cash = metrics["unreconciled_cash"]
unapproved_journals = metrics["unapproved_journals"]
intercompany_exceptions = metrics["intercompany_exceptions"]
overdue_ap = metrics["overdue_ap"]
manual_pct = metrics["manual_journal_pct"]
ai_awaiting_review = metrics["ai_recommendations_awaiting_review"]
data_quality_exceptions = metrics["data_quality_exceptions"]

overall_close_pct = (
    round(100.0 * close_progress["posted_count"].sum() / close_progress["total_journals"].sum(), 1)
    if close_progress["total_journals"].sum() else 0.0
)
unapproved_total = float(unapproved_journals["amount"].sum()) if len(unapproved_journals) else 0.0
overdue_total = float(overdue_ap["amount"].sum()) if len(overdue_ap) else 0.0

# --- KPI row -----------------------------------------------------------

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Close progress", f"{overall_close_pct}%")
k2.metric("Manual journal %", f"{manual_pct['manual_pct']}%", help=f"{manual_pct['manual_count']}/{manual_pct['total_count']} journals")
k3.metric("Unapproved journals", f"{len(unapproved_journals)}", help=f"£/$ {unapproved_total:,.2f} total")
k4.metric("Overdue AP", f"{len(overdue_ap)}", help=f"£/$ {overdue_total:,.2f} total")
k5.metric("Outstanding reconciliations", outstanding["bank_outstanding"] + outstanding["intercompany_outstanding"],
          help=f"{outstanding['bank_outstanding']} bank + {outstanding['intercompany_outstanding']} intercompany")

st.divider()

# --- Close progress ------------------------------------------------------

st.subheader("Close progress by entity / period")
st.dataframe(close_progress, width='stretch', hide_index=True)

st.divider()

# --- Reconciliation ------------------------------------------------------

col1, col2 = st.columns(2)
with col1:
    st.subheader("Unreconciled cash")
    if len(unreconciled_cash):
        st.dataframe(unreconciled_cash, width='stretch', hide_index=True)
    else:
        st.success("No unreconciled bank transactions.")

with col2:
    st.subheader("Intercompany exceptions")
    if len(intercompany_exceptions):
        st.dataframe(
            intercompany_exceptions[["intercompany_transaction_id", "entity_from_code", "entity_to_code",
                                      "amount", "currency", "match_status"]],
            width='stretch', hide_index=True,
        )
    else:
        st.success("No intercompany exceptions.")

st.divider()

# --- Journals and AP -------------------------------------------------------

col3, col4 = st.columns(2)
with col3:
    st.subheader("Unapproved journals")
    if len(unapproved_journals):
        st.dataframe(unapproved_journals, width='stretch', hide_index=True)
    else:
        st.success("No unapproved journals.")

with col4:
    st.subheader("Overdue AP")
    if len(overdue_ap):
        st.dataframe(overdue_ap, width='stretch', hide_index=True)
    else:
        st.success("No overdue AP invoices.")

st.divider()

# --- AI + data quality ----------------------------------------------------

st.subheader("AI recommendations awaiting review")
st.caption(
    "Live result of 08-accounting-automation's vendor→account rule — an account mismatch is "
    "exactly the kind of ambiguous case 09-ai's AI assistant exists to help a human review, "
    "per the rules-before-AI principle from Phase 11/12."
)
if len(ai_awaiting_review):
    st.dataframe(ai_awaiting_review, width='stretch', hide_index=True)
else:
    st.success("Nothing awaiting AI-assisted review.")

st.subheader("Data-quality exceptions")
st.caption("Live result of three of 08-accounting-automation's exception rules: duplicate invoices, missing required fields, and intercompany transactions with no counterpart.")
if len(data_quality_exceptions):
    summary = data_quality_exceptions.groupby("rule").size().reset_index(name="count")
    st.dataframe(summary, width='stretch', hide_index=True)
    with st.expander("Full detail"):
        st.dataframe(data_quality_exceptions, width='stretch', hide_index=True)
else:
    st.success("No data-quality exceptions found.")
