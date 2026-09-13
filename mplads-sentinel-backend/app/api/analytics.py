from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import query_service as qs

router = APIRouter()


@router.get("")
def analytics(
    house: str = Query("", description="Lok Sabha or Rajya Sabha; omit for all houses"),
    db: Session = Depends(get_db),
):
    return qs.get_analytics_data(db, house=qs.normalize_house(house))
