# Security Model — Northstar Finance OS

Documents the security approach at the architecture level, per PLAN.md §32. **This is design documentation, not an implemented control** — nothing here is enforced by running code until the relevant phase (API in Phase 10, AI controls in Phase 12) builds it. This is a portfolio proof-of-concept, not a production-secure ERP; limitations are stated explicitly at the end.

## Authentication (concept-level)

Users authenticate to the API layer (built in Phase 10) via a token-based scheme (e.g. bearer token / API key per user or service). No production identity provider integration is in scope — this is documented as a concept to show the design is auth-aware, not implemented as a full auth system.

## Authorisation / role-based access

Role-based access enforces segregation of duties, directly satisfying **R12** (no self-approved journals above threshold):

| Role | Can do | Cannot do |
|---|---|---|
| Ingestion service | Write raw/staged transactions into the exception queue or data model | Approve or post journals |
| Preparer / Maker | Create and submit journal entries, resolve exceptions | Approve their own journal entries |
| Approver / Checker | Approve journals submitted by a different user, review exception queue | Approve a journal they created themselves |
| Controller / CFO (viewer) | Read trial balance, close dashboard, management reporting | Edit posted journals directly |

The maker/checker separation is enforced at the Journal Engine and Approvals layer described in [system-architecture.md](./system-architecture.md), not left to convention — this is the direct fix for the current-state gap documented in [process-analysis.md](../02-process-mapping/process-analysis.md) ("no system of record for approvals").

## Secrets management

Follows the pattern already established in the repo root: real secrets are never committed. `.env.example` documents every required environment variable name with a placeholder value; actual values live only in a local, gitignored `.env`. No API keys, passwords, or credentials appear anywhere in this repository.

## Least privilege

Each role above has the minimum access needed for its function — the ingestion service can write staged data but not approve or post; a preparer can create journals but not approve their own; a viewer role exists specifically so CFO/Controller reporting access doesn't require posting access. This mirrors segregation-of-duties expectations from the current-state audit/controls background (ICFR/PCAOB) rather than introducing a novel model.

## Audit logging

Every posting and every edit is written to an immutable audit log, attributable to a user and timestamp — this is the direct fix for **R11** (no system-enforced audit trail today). The audit log is a Controls-layer component in [system-architecture.md](./system-architecture.md) and covers:
- journal creation, approval, posting
- AI-suggested treatments and whether a human accepted, overrode, or rejected them (PLAN.md §25 — overrides must be logged with a reason)
- exception-queue entry and resolution

## Sensitive data handling

Reaffirms the rule already established in `AGENTS.md`: no real customer data, no real employer/confidential data, no real personal financial information anywhere in this project. All data used from Phase 7 onward (`04-data/`) is synthetic and generated specifically to be messy in realistic, documented ways — never sourced from an actual company.

## Stated limitations

This architecture is designed to be credible and internally consistent, not production-secure:
- No real identity provider, MFA, or session management is implemented
- No penetration testing, encryption-at-rest configuration, or network security design is in scope
- Role-based access is enforced at the application logic level as documented, not backed by a full IAM system
- This document exists to demonstrate security-aware architecture thinking for a solutions-consulting context, not to certify the system for real financial data
