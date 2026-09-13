from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import query_service as qs

router = APIRouter()


@router.get("")
def risk_overview(
    house: str = Query("", description="Lok Sabha or Rajya Sabha; omit for all houses"),
    db: Session = Depends(get_db),
):
    house = qs.normalize_house(house)
    return {
        "summary": qs.get_dashboard_summary(db, house=house),
        "high_risk_works": qs.get_high_risk_works(db, limit=10, house=house),
    }


@router.get("/{work_id:path}")
def risk_analysis(work_id: str, db: Session = Depends(get_db)):
    data = qs.get_risk_analysis(db, work_id)
    if not data:
        raise HTTPException(status_code=404, detail="Risk analysis not found")
    return data
