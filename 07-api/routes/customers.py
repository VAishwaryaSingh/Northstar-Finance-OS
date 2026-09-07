from fastapi import APIRouter, Depends, status

import models
from auth import require_api_key
from db import get_engine
from schemas import CustomerCreate, CustomerOut

router = APIRouter(tags=["customers"], dependencies=[Depends(require_api_key)])


@router.post("/customers", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate):
    engine = get_engine()
    with engine.begin() as conn:
        return models.create_customer(conn, payload)
