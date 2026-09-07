# ADR-0001: PostgreSQL as the primary database

## Context

The Finance Data Model ([system-architecture.md](../03-architecture/system-architecture.md)) needs a relational database that can enforce referential integrity across entities, customers, vendors, chart of accounts, invoices, payments, bank transactions, journal entries/lines, intercompany transactions, and FX rates (PLAN.md §18), and that credibly demonstrates production-realistic relational database capability to a solutions-consulting audience.

## Options considered

- **PostgreSQL** — full-featured open-source RDBMS, strong constraint/transaction support, industry-standard for real ERP/finance backends
- **SQLite** — zero-setup, file-based, adequate for a first pass but weaker on concurrent writes and some constraint features
- **A managed cloud database** — realistic for production but adds cost/setup overhead inappropriate for a local portfolio project

## Decision

Use PostgreSQL as the primary target database (PLAN.md §20). SQLite remains acceptable as a first-iteration fallback only if local environment constraints make PostgreSQL genuinely inconvenient to set up — but PostgreSQL is the default target because it demonstrates realistic relational database capability, which SQLite does not fully.

## Trade-offs

- PostgreSQL requires local setup (or a container) versus SQLite's zero-config file; this is worth it for the credibility of the demonstration
- A managed cloud database would be more "production-realistic" still, but introduces cost, account setup, and hosting/security concerns out of proportion to a local portfolio POC

## Consequences

- `05-sql/schema.sql` and all query sets (AP, reconciliation, intercompany, close, reporting, controls) target PostgreSQL syntax
- The Python ingestion pipeline (Phase 9) uses SQLAlchemy against PostgreSQL, keeping SQLite viable as a drop-in fallback if needed since SQLAlchemy abstracts the connection
