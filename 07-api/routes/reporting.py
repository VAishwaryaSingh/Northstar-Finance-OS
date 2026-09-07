from typing import Optional

from fastapi import APIRouter, Depends, Query

import models
from auth import require_api_key
from db import get_engine
from schemas import (
    CloseStatusRow,
    IntercompanyExceptionRow,
    ReconciliationStatusRow,
    TrialBalanceRow,
)

router = APIRouter(tags=["reporting"], dependencies=[Depends(require_api_key)])


@router.get("/trial-balance", response_model=list[TrialBalanceRow])
def trial_balance(entity_code: Optional[str] = Query(default=None)):
    engine = get_engine()
    with engine.connect() as conn:
        return models.get_trial_balance(conn, entity_code)


@router.get("/reconciliation-status", response_model=list[ReconciliationStatusRow])
def reconciliation_status(entity_code: Optional[str] = Query(default=None)):
    engine = get_engine()
    with engine.connect() as conn:
        return models.get_reconciliation_status(conn, entity_code)


@router.get("/close-status", response_model=list[CloseStatusRow])
def close_status(entity_code: Optional[str] = Query(default=None), period: Optional[str] = Query(default=None)):
    engine = get_engine()
    with engine.connect() as conn:
        return models.get_close_status(conn, entity_code, period)


@router.get("/intercompany-exceptions", response_model=list[IntercompanyExceptionRow])
def intercompany_exceptions(entity_code: Optional[str] = Query(default=None)):
    engine = get_engine()
    with engine.connect() as conn:
        return models.get_intercompany_exceptions(conn, entity_code)
