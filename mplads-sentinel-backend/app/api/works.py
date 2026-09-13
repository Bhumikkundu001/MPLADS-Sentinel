from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import query_service as qs

router = APIRouter()


@router.get("")
def list_works(
    q: str = Query("", description="Search query (name, description, id, state, constituency, MP name)"),
    state: str = Query(""),
    risk_level: str = Query("", description="Deprecated alias — use `risk`"),
    risk: str = Query("", description="Filter by risk_level: High, Medium, or Low"),
    status: str = Query(""),
    house: str = Query("", description="Lok Sabha or Rajya Sabha"),
    data_source: str = Query("", description="demo_seed, lok_sabha_real, or rajya_sabha_real"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    effective_risk_level = risk or risk_level
    return qs.search_works(
        db,
        query=q,
        state=state,
        risk_level=effective_risk_level,
        status=status,
        house=house,
        data_source=data_source,
        limit=limit,
        offset=offset,
    )


# NOTE: `/{work_id:path}/similar` must be registered BEFORE the plain
# `/{work_id:path}` route below. FastAPI/Starlette matches routes in
# registration order, and `:path` is a greedy converter — if the plain
# catch-all were registered first, it would swallow ".../similar" as part
# of work_id and this endpoint would never be reached.
@router.get("/{work_id:path}/similar")
def get_similar(work_id: str, limit: int = Query(5, le=20), db: Session = Depends(get_db)):
    work = qs.get_work_by_id(db, work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    similar = qs.get_similar_works(db, work_id, limit=limit)
    return {"work_id": work_id, "similar_works": similar}


@router.get("/{work_id:path}")
def get_work(work_id: str, db: Session = Depends(get_db)):
    # Real work IDs (e.g. "WS/MP005/2024-2025/145074") contain literal "/" —
    # the default FastAPI path parameter stops at the first "/", which silently
    # 404'd on the vast majority of real records. The `:path` converter matches
    # the full remainder of the path instead.
    work = qs.get_work_by_id(db, work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    return work
