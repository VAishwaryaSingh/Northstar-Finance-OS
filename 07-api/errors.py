"""API-level exceptions, translated to HTTP responses by main.py's
exception handlers rather than each route deciding a status code itself.
"""

from __future__ import annotations


class NotFoundError(Exception):
    """A referenced business key (entity_code, invoice_id, ...) doesn't exist."""


class BusinessRuleError(Exception):
    """A request is well-formed but violates an accounting rule the
    database itself would also reject (e.g. an unbalanced journal slipping
    past schema validation some other way). Maps to HTTP 400."""
