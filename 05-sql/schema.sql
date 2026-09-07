-- Northstar Finance OS — Relational Schema (PostgreSQL)
--
-- Implements 03-architecture/data-model.md exactly: all 14 tables, the
-- debit = credit rule, and the maker != checker (segregation of duties)
-- rule, enforced here as real database constraints and triggers rather
-- than left as documentation. See ADR-0001 for why PostgreSQL.
--
-- Run:  psql -d northstar -f 05-sql/schema.sql

BEGIN;

-- ===========================================================================
-- Reference / master data
-- ===========================================================================

CREATE TABLE entities (
    entity_id            VARCHAR(20) PRIMARY KEY,
    entity_code          VARCHAR(20) NOT NULL UNIQUE,
    entity_name          TEXT NOT NULL,
    country               TEXT NOT NULL,
    functional_currency   CHAR(3) NOT NULL,
    status                VARCHAR(10) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive'))
);

CREATE TABLE users (
    user_id   VARCHAR(20) PRIMARY KEY,
    name      TEXT NOT NULL,
    email     TEXT NOT NULL UNIQUE,
    role      VARCHAR(20) NOT NULL CHECK (role IN ('preparer', 'approver', 'viewer', 'ingestion_service', 'admin')),
    status    VARCHAR(10) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive'))
);

CREATE TABLE chart_of_accounts (
    account_id       VARCHAR(20) PRIMARY KEY,
    account_code     VARCHAR(10) NOT NULL UNIQUE,
    account_name     TEXT NOT NULL,
    account_type     VARCHAR(10) NOT NULL CHECK (account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense')),
    normal_balance   VARCHAR(6) NOT NULL CHECK (normal_balance IN ('debit', 'credit')),
    status           VARCHAR(10) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive'))
);

CREATE TABLE customers (
    customer_id       VARCHAR(20) PRIMARY KEY,
    customer_code     VARCHAR(10) NOT NULL UNIQUE,
    customer_name     TEXT NOT NULL,
    entity_id         VARCHAR(20) NOT NULL REFERENCES entities(entity_id),
    billing_currency  CHAR(3) NOT NULL,
    status            VARCHAR(10) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive'))
);

CREATE TABLE vendors (
    vendor_id           VARCHAR(20) PRIMARY KEY,
    vendor_code         VARCHAR(10) NOT NULL UNIQUE,
    vendor_name         TEXT NOT NULL,
    default_account_id  VARCHAR(20) REFERENCES chart_of_accounts(account_id),
    status               VARCHAR(10) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive'))
);

-- ===========================================================================
-- Transactions
--
-- Every transaction table below carries entity_id, a date, currency, source
-- and status, per data-model.md's "mandatory transaction fields" rule.
-- ===========================================================================

CREATE TABLE invoices (
    invoice_id      VARCHAR(20) PRIMARY KEY,
    invoice_type    VARCHAR(2) NOT NULL CHECK (invoice_type IN ('AR', 'AP')),
    invoice_number  VARCHAR(60) NOT NULL,
    entity_id       VARCHAR(20) NOT NULL REFERENCES entities(entity_id),
    customer_id     VARCHAR(20) REFERENCES customers(customer_id),
    vendor_id       VARCHAR(20) REFERENCES vendors(vendor_id),
    invoice_date    DATE NOT NULL,
    due_date        DATE,
    currency        CHAR(3) NOT NULL,
    amount          NUMERIC(18, 2) NOT NULL,
    source          TEXT NOT NULL,
    account_id      VARCHAR(20) REFERENCES chart_of_accounts(account_id),
    status          VARCHAR(20) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'paid', 'void', 'duplicate_flagged')),
    CONSTRAINT invoices_type_party_chk CHECK (
        (invoice_type = 'AR' AND customer_id IS NOT NULL AND vendor_id IS NULL) OR
        (invoice_type = 'AP' AND vendor_id IS NOT NULL AND customer_id IS NULL)
    )
    -- Deliberately no UNIQUE(entity_id, invoice_number) here: R10's fix is
    -- automated *detection* of duplicate invoices (see 05-sql/ap.sql), not a
    -- blind database constraint -- invoice numbers are known to be reused
    -- across entities in the legacy system (discovery-notes.md), and a hard
    -- constraint would just as easily hide a legitimate re-issued invoice.
);

CREATE TABLE payments (
    payment_id    VARCHAR(20) PRIMARY KEY,
    entity_id     VARCHAR(20) NOT NULL REFERENCES entities(entity_id),
    invoice_id    VARCHAR(20) REFERENCES invoices(invoice_id),
    payment_date  DATE NOT NULL,
    currency      CHAR(3) NOT NULL,
    amount        NUMERIC(18, 2) NOT NULL,
    payment_type  VARCHAR(10) NOT NULL CHECK (payment_type IN ('received', 'made')),
    source        TEXT NOT NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'matched', 'unmatched'))
);

CREATE TABLE bank_transactions (
    bank_transaction_id  VARCHAR(20) PRIMARY KEY,
    entity_id             VARCHAR(20) NOT NULL REFERENCES entities(entity_id),
    bank_account_code     VARCHAR(30) NOT NULL,
    transaction_date      DATE NOT NULL,
    currency              CHAR(3) NOT NULL,
    amount                NUMERIC(18, 2) NOT NULL,
    description           TEXT,
    source                TEXT NOT NULL,
    match_status          VARCHAR(20) NOT NULL DEFAULT 'unmatched' CHECK (match_status IN ('unmatched', 'probable_match', 'matched', 'exception')),
    matched_payment_id    VARCHAR(20) REFERENCES payments(payment_id)
);

CREATE TABLE journal_entries (
    journal_entry_id  VARCHAR(20) PRIMARY KEY,
    entity_id         VARCHAR(20) NOT NULL REFERENCES entities(entity_id),
    entry_date        DATE NOT NULL,
    period            VARCHAR(7) NOT NULL,  -- 'YYYY-MM'
    currency          CHAR(3) NOT NULL,
    source            VARCHAR(20) NOT NULL CHECK (source IN ('system', 'manual', 'ai_assisted')),
    classification    TEXT NOT NULL,
    status            VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'pending_approval', 'approved', 'posted', 'rejected')),
    created_by        VARCHAR(20) NOT NULL REFERENCES users(user_id),
    approved_by       VARCHAR(20) REFERENCES users(user_id),
    description       TEXT,
    -- R12: a journal can never be approved by the person who created it.
    CONSTRAINT journal_entries_maker_checker_chk CHECK (approved_by IS NULL OR approved_by <> created_by)
);

CREATE TABLE journal_lines (
    journal_line_id    VARCHAR(20) PRIMARY KEY,
    journal_entry_id   VARCHAR(20) NOT NULL REFERENCES journal_entries(journal_entry_id) ON DELETE CASCADE,
    account_id         VARCHAR(20) NOT NULL REFERENCES chart_of_accounts(account_id),
    debit_amount       NUMERIC(18, 2) NOT NULL DEFAULT 0 CHECK (debit_amount >= 0),
    credit_amount      NUMERIC(18, 2) NOT NULL DEFAULT 0 CHECK (credit_amount >= 0),
    line_description   TEXT,
    -- each line moves exactly one side of the entry
    CONSTRAINT journal_lines_one_side_chk CHECK (
        (debit_amount > 0 AND credit_amount = 0) OR (credit_amount > 0 AND debit_amount = 0)
    )
);

CREATE TABLE intercompany_transactions (
    intercompany_transaction_id  VARCHAR(20) PRIMARY KEY,
    entity_from_id                VARCHAR(20) NOT NULL REFERENCES entities(entity_id),
    entity_to_id                  VARCHAR(20) NOT NULL REFERENCES entities(entity_id),
    transaction_date              DATE NOT NULL,
    currency                      CHAR(3) NOT NULL,
    amount                        NUMERIC(18, 2) NOT NULL,
    reference                     VARCHAR(60) NOT NULL,
    source                        TEXT NOT NULL,
    match_status                  VARCHAR(20) NOT NULL DEFAULT 'unmatched' CHECK (match_status IN ('unmatched', 'matched', 'exception')),
    related_journal_entry_id      VARCHAR(20) REFERENCES journal_entries(journal_entry_id),
    CONSTRAINT intercompany_entities_differ_chk CHECK (entity_from_id <> entity_to_id)
);

CREATE TABLE fx_rates (
    fx_rate_id     VARCHAR(20) PRIMARY KEY,
    currency_from  CHAR(3) NOT NULL,
    currency_to    CHAR(3) NOT NULL,
    rate_date      DATE NOT NULL,
    rate           NUMERIC(18, 8) NOT NULL CHECK (rate > 0),
    source         TEXT NOT NULL,
    UNIQUE (currency_from, currency_to, rate_date)
);

-- ===========================================================================
-- Controls
-- ===========================================================================

CREATE TABLE approvals (
    approval_id        VARCHAR(20) PRIMARY KEY,
    journal_entry_id   VARCHAR(20) NOT NULL REFERENCES journal_entries(journal_entry_id),
    approver_id        VARCHAR(20) NOT NULL REFERENCES users(user_id),
    decision            VARCHAR(10) NOT NULL CHECK (decision IN ('approved', 'rejected')),
    decision_date        TIMESTAMP NOT NULL DEFAULT now(),
    comments             TEXT
);

CREATE TABLE audit_logs (
    audit_log_id   BIGSERIAL PRIMARY KEY,
    table_name     TEXT NOT NULL,
    record_id      TEXT NOT NULL,
    action         VARCHAR(10) NOT NULL CHECK (action IN ('insert', 'update', 'approve', 'reject', 'override')),
    performed_by   VARCHAR(20) NOT NULL REFERENCES users(user_id),
    performed_at   TIMESTAMP NOT NULL DEFAULT now(),
    before_value   JSONB,
    after_value    JSONB,
    reason         TEXT,
    -- AI safety policy (PLAN.md §25): an override is never logged without why.
    CONSTRAINT audit_logs_override_reason_chk CHECK (action <> 'override' OR reason IS NOT NULL)
);

-- ===========================================================================
-- Indexes on commonly-filtered/joined columns
-- ===========================================================================

CREATE INDEX idx_invoices_entity_status ON invoices(entity_id, status);
CREATE INDEX idx_payments_invoice ON payments(invoice_id);
CREATE INDEX idx_bank_transactions_match_status ON bank_transactions(match_status);
CREATE INDEX idx_journal_entries_period ON journal_entries(entity_id, period);
CREATE INDEX idx_journal_lines_entry ON journal_lines(journal_entry_id);
CREATE INDEX idx_intercompany_match_status ON intercompany_transactions(match_status);

-- ===========================================================================
-- Enforced accounting rule #1: debit = credit
--
-- A journal entry's lines are allowed to be built up incrementally while the
-- header is in 'draft' status. The moment the entry is not in 'draft' status,
-- its lines must sum to zero net (total debits = total credits). This is
-- checked as a DEFERRABLE constraint trigger on journal_lines so that, within
-- one transaction, the header and all of its lines can be inserted together
-- and the balance is only verified once, at commit.
-- ===========================================================================

CREATE OR REPLACE FUNCTION enforce_balanced_journal() RETURNS TRIGGER AS $$
DECLARE
    je_id      VARCHAR(20);
    je_status  VARCHAR(20);
    total_debit   NUMERIC(18, 2);
    total_credit  NUMERIC(18, 2);
BEGIN
    je_id := COALESCE(NEW.journal_entry_id, OLD.journal_entry_id);
    SELECT status INTO je_status FROM journal_entries WHERE journal_entry_id = je_id;

    IF je_status IS NOT NULL AND je_status <> 'draft' THEN
        SELECT COALESCE(SUM(debit_amount), 0), COALESCE(SUM(credit_amount), 0)
          INTO total_debit, total_credit
          FROM journal_lines
         WHERE journal_entry_id = je_id;

        IF total_debit <> total_credit THEN
            RAISE EXCEPTION 'Journal entry % is not balanced outside draft status: debits % <> credits % (status=%)',
                je_id, total_debit, total_credit, je_status;
        END IF;
    END IF;
    RETURN NULL;  -- AFTER trigger: return value is ignored
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER trg_journal_lines_balanced
    AFTER INSERT OR UPDATE OR DELETE ON journal_lines
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW
    EXECUTE FUNCTION enforce_balanced_journal();

-- ===========================================================================
-- Enforced accounting rule #2: maker != checker
--
-- journal_entries already blocks approved_by = created_by (CHECK constraint
-- above). This trigger closes the same gap for the approvals table, so the
-- system of record for sign-off (approvals) can never disagree with it.
-- ===========================================================================

CREATE OR REPLACE FUNCTION enforce_maker_checker_on_approval() RETURNS TRIGGER AS $$
DECLARE
    je_creator VARCHAR(20);
BEGIN
    SELECT created_by INTO je_creator FROM journal_entries WHERE journal_entry_id = NEW.journal_entry_id;
    IF je_creator = NEW.approver_id THEN
        RAISE EXCEPTION 'Approver % cannot approve journal entry % they created (maker/checker violation)',
            NEW.approver_id, NEW.journal_entry_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_enforce_maker_checker_on_approval
    BEFORE INSERT ON approvals
    FOR EACH ROW
    EXECUTE FUNCTION enforce_maker_checker_on_approval();

COMMIT;
