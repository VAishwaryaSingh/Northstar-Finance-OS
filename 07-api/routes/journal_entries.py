from fastapi import APIRouter, Depends, status

import models
from auth import require_api_key
from db import get_engine
from schemas import JournalEntryCreate, JournalEntryOut

router = APIRouter(tags=["journal-entries"], dependencies=[Depends(require_api_key)])


@router.post("/journal-entries", response_model=JournalEntryOut, status_code=status.HTTP_201_CREATED)
def create_journal_entry(payload: JournalEntryCreate):
    """The balanced-debits-equal-credits and maker!=checker rules are
    already enforced client-side by schemas.JournalEntryCreate's
    validators (a clean 422 on violation) -- but schema.sql's deferred
    trigger and CHECK constraint enforce the same rules again at the
    database level as the actual source of truth, since a client-side
    check alone would only be advisory."""
    engine = get_engine()
    with engine.begin() as conn:
        return models.create_journal_entry(conn, payload)
