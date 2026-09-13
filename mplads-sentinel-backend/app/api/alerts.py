from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import query_service as qs

router = APIRouter()


@router.get("")
def get_alerts(
    limit: int = Query(20, le=50),
    house: str = Query("", description="Lok Sabha or Rajya Sabha; omit for all houses"),
    db: Session = Depends(get_db),
):
    return {"alerts": qs.get_alerts(db, limit=limit, house=qs.normalize_house(house))}
