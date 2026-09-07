from fastapi import APIRouter, Depends, status

import models
from auth import require_api_key
from db import get_engine
from schemas import PaymentCreate, PaymentOut

router = APIRouter(tags=["payments"], dependencies=[Depends(require_api_key)])


@router.post("/payments", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(payload: PaymentCreate):
    engine = get_engine()
    with engine.begin() as conn:
        return models.create_payment(conn, payload)
