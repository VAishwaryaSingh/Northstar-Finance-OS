from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

import models
from auth import require_api_key
from db import get_engine
from schemas import InvoiceCreate, InvoiceOut

router = APIRouter(tags=["invoices"], dependencies=[Depends(require_api_key)])


@router.post("/invoices", response_model=InvoiceOut)
def create_invoice(payload: InvoiceCreate) -> JSONResponse:
    """Idempotent on (entity_code, invoice_number, invoice_type): a replay
    with the same amount returns the existing invoice (200 OK), not a new
    one. A genuinely new invoice number returns 201 Created. A same-number/
    different-amount replay is inserted flagged as a duplicate (see
    models.create_invoice) and also returns 201, since a new row really
    was created -- just one that needs review, per R10."""
    engine = get_engine()
    with engine.begin() as conn:
        invoice, is_replay = models.create_invoice(conn, payload)
    invoice["idempotent_replay"] = is_replay
    status_code = status.HTTP_200_OK if is_replay else status.HTTP_201_CREATED
    return JSONResponse(status_code=status_code, content=InvoiceOut(**invoice).model_dump(mode="json"))
