"""
Safe, parameterized database query functions.
The LLM never touches the database directly — all retrieval goes through here.
"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc, Integer, cast
from app.models.work import Work, WorkSimilarity

# The only two real house values in the dataset. Anything else (typos, stray
# query params, arbitrary strings) must never be silently applied as a filter
# — that would produce a confidently-wrong "combined" or empty result set
# rather than an honest "all houses" fallback.
ALLOWED_HOUSES = {"Lok Sabha", "Rajya Sabha"}


def normalize_house(house: Optional[str]) -> Optional[str]:
    """Returns the exact house value if valid, otherwise None (= all houses)."""
    if not house:
        return None
    for allowed in ALLOWED_HOUSES:
        if house.strip().lower() == allowed.lower():
            return allowed
    return None


# ── Works ─────────────────────────────────────────────────────────────────────

def get_work_by_id(db: Session, work_id: str) -> Optional[dict]:
    work = db.query(Work).filter(Work.id == work_id).first()
    return work.to_dict() if work else None


def search_works(
    db: Session,
    query: str = "",
    state: str = "",
    risk_level: str = "",
    status: str = "",
    house: str = "",
    data_source: str = "",
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """All filtering/sorting/pagination happens at the database level (SQL
    WHERE/ORDER BY/LIMIT/OFFSET) — the full works table (38,265 real rows in
    staging) is never loaded into Python for this."""
    q = db.query(Work)
    if query:
        pattern = f"%{query}%"
        q = q.filter(
            or_(
                Work.name.ilike(pattern),
                Work.description.ilike(pattern),
                Work.constituency.ilike(pattern),
                Work.district.ilike(pattern),
                Work.mp_name.ilike(pattern),
                Work.state.ilike(pattern),
                Work.id.ilike(pattern),
            )
        )
    if state:
        q = q.filter(Work.state.ilike(f"%{state}%"))
    if risk_level:
        q = q.filter(Work.risk_level == risk_level)
    if status:
        q = q.filter(Work.status.ilike(f"%{status}%"))
    if house:
        q = q.filter(Work.house.ilike(f"%{house}%"))
    if data_source:
        q = q.filter(Work.data_source == data_source)

    total = q.count()
    works = q.order_by(desc(Work.risk_score)).offset(offset).limit(limit).all()
    items = [w.to_dict() for w in works]
    return {
        # "items"/"limit"/"offset" are the Phase 6 structured-pagination contract.
        # "total" and "works" are kept for backward compatibility with the current
        # frontend (Works.jsx reads res.works) until Phase 7 updates it — "works"
        # and "items" are always the same list.
        "items": items,
        "works": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_high_risk_works(db: Session, limit: int = 10, house: Optional[str] = None) -> list[dict]:
    q = db.query(Work).filter(Work.risk_level == "High")
    if house:
        q = q.filter(Work.house == house)
    works = q.order_by(desc(Work.risk_score)).limit(limit).all()
    return [w.to_dict() for w in works]


def get_works_requiring_review(db: Session, limit: int = 10, house: Optional[str] = None) -> list[dict]:
    q = db.query(Work).filter(Work.risk_status == "Requires Review")
    if house:
        q = q.filter(Work.house == house)
    works = q.order_by(desc(Work.risk_score)).limit(limit).all()
    return [w.to_dict() for w in works]


# ── Risk & Anomalies ──────────────────────────────────────────────────────────

def get_risk_analysis(db: Session, work_id: str) -> Optional[dict]:
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        return None
    similar = get_similar_works(db, work_id, limit=5)
    return {
        "work_id": work.id,
        "work_name": work.name,
        "house": work.house,
        "state": work.state,
        "constituency": work.constituency,
        "risk_score": work.risk_score,
        "risk_level": work.risk_level,
        "risk_status": work.risk_status,
        "anomaly_score": work.anomaly_score,
        "is_anomaly": work.is_anomaly,
        "indicators": work.risk_indicators,
        "similar_works": similar,
        "financial": {
            "recommended_amount": work.recommended_amount,
            "sanctioned_amount": work.sanctioned_amount,
            "expenditure": work.expenditure,
            "cost_deviation_pct": work.cost_deviation_pct,
        },
        "progress": work.progress,
        "status": work.status,
    }


def get_anomaly_works(db: Session, limit: int = 10, house: Optional[str] = None) -> list[dict]:
    q = db.query(Work).filter(Work.is_anomaly == True)
    if house:
        q = q.filter(Work.house == house)
    works = q.order_by(Work.anomaly_score).limit(limit).all()   # lower score = more anomalous in IF
    return [w.to_dict() for w in works]


def get_expenditure_anomalies(db: Session, limit: int = 10) -> list[dict]:
    """Works where expenditure deviates significantly from sanctioned amount."""
    works = db.query(Work).filter(
        Work.expenditure.isnot(None),
        Work.sanctioned_amount.isnot(None),
        Work.sanctioned_amount > 0,
    ).all()

    flagged = []
    for w in works:
        dev = abs(w.cost_deviation_pct)
        if dev >= 20:
            d = w.to_dict()
            d["deviation_abs_pct"] = dev
            flagged.append(d)

    flagged.sort(key=lambda x: x["deviation_abs_pct"], reverse=True)
    return flagged[:limit]


# ── Similarity ────────────────────────────────────────────────────────────────

def get_similar_works(db: Session, work_id: str, limit: int = 5) -> list[dict]:
    sims = (
        db.query(WorkSimilarity)
        .filter(WorkSimilarity.work_id == work_id)
        .order_by(desc(WorkSimilarity.similarity_score))
        .limit(limit)
        .all()
    )
    return [s.to_dict() for s in sims]


# ── Aggregate / Dashboard ─────────────────────────────────────────────────────

def get_dashboard_summary(db: Session, house: Optional[str] = None) -> dict:
    def base():
        q = db.query(Work)
        if house:
            q = q.filter(Work.house == house)
        return q

    total = base().count()
    high = base().filter(Work.risk_level == "High").count()
    medium = base().filter(Work.risk_level == "Medium").count()
    low = base().filter(Work.risk_level == "Low").count()
    review = base().filter(Work.risk_status == "Requires Review").count()
    anomalies = base().filter(Work.is_anomaly == True).count()
    completed = base().filter(Work.is_reported_complete == True).count()
    total_exp = base().with_entities(func.sum(Work.expenditure)).scalar() or 0
    total_sanc = base().with_entities(func.sum(Work.sanctioned_amount)).scalar() or 0
    avg_risk = base().with_entities(func.avg(Work.risk_score)).scalar() or 0

    return {
        "total_works": total,
        "high_risk": high,
        "medium_risk": medium,
        "low_risk": low,
        "requires_review": review,
        "anomalies_detected": anomalies,
        "completed": completed,
        "completion_rate": round(completed / total * 100, 1) if total else 0,
        "total_expenditure_lakhs": round(total_exp, 2),
        "total_sanctioned_lakhs": round(total_sanc, 2),
        "avg_risk_score": round(avg_risk, 1),
    }


def get_state_risk_summary(db: Session, state: str = None, house: Optional[str] = None) -> list[dict]:
    q = db.query(
        Work.state,
        func.count(Work.id).label("total"),
        func.sum(cast(Work.risk_level == "High", Integer)).label("high"),
        func.sum(cast(Work.risk_level == "Medium", Integer)).label("medium"),
        func.sum(cast(Work.risk_level == "Low", Integer)).label("low"),
        func.avg(Work.risk_score).label("avg_risk"),
    ).group_by(Work.state)
    if state:
        q = q.filter(Work.state.ilike(f"%{state}%"))
    if house:
        q = q.filter(Work.house == house)
    rows = q.order_by(desc("high")).all()
    return [
        {
            "state": r.state,
            "total": r.total,
            "high_risk": int(r.high or 0),
            "medium_risk": int(r.medium or 0),
            "low_risk": int(r.low or 0),
            "avg_risk_score": round(float(r.avg_risk or 0), 1),
        }
        for r in rows
    ]


def get_constituency_risk_summary(db: Session, constituency: str) -> Optional[dict]:
    works = db.query(Work).filter(Work.constituency.ilike(f"%{constituency}%")).all()
    if not works:
        return None
    high = sum(1 for w in works if w.risk_level == "High")
    medium = sum(1 for w in works if w.risk_level == "Medium")
    low = sum(1 for w in works if w.risk_level == "Low")
    avg_risk = sum(w.risk_score for w in works) / len(works)
    return {
        "constituency": works[0].constituency,
        "state": works[0].state,
        "mp_name": works[0].mp_name,
        "total": len(works),
        "high_risk": high,
        "medium_risk": medium,
        "low_risk": low,
        "avg_risk_score": round(avg_risk, 1),
        "top_works": sorted(
            [w.to_dict() for w in works], key=lambda x: x["risk_score"], reverse=True
        )[:5],
    }


def get_analytics_data(db: Session, house: Optional[str] = None) -> dict:
    summary = get_dashboard_summary(db, house=house)
    state_summary = get_state_risk_summary(db, house=house)
    top_high_risk = get_high_risk_works(db, limit=5, house=house)

    category_q = db.query(Work.category, func.count(Work.id).label("count"))
    status_q = db.query(Work.status, func.count(Work.id).label("count"))
    if house:
        category_q = category_q.filter(Work.house == house)
        status_q = status_q.filter(Work.house == house)
    category_q = category_q.group_by(Work.category).all()
    status_q = status_q.group_by(Work.status).all()

    by_category = [{"category": r.category, "count": r.count} for r in category_q]
    by_status = [{"status": r.status, "count": r.count} for r in status_q]

    return {
        "summary": summary,
        "by_state": state_summary,
        "by_category": by_category,
        "by_status": by_status,
        "top_high_risk": top_high_risk,
    }


def get_alerts(db: Session, limit: int = 20, house: Optional[str] = None) -> list[dict]:
    q = db.query(Work).filter(Work.risk_score >= 60)
    if house:
        q = q.filter(Work.house == house)
    works = q.order_by(desc(Work.risk_score)).limit(limit).all()
    alerts = []
    for w in works:
        indicators = w.risk_indicators
        primary = indicators[0] if indicators else "Risk indicator"
        alerts.append({
            "id": w.id,
            "work_id": w.id,
            "work_name": w.name,
            "state": w.state,
            "constituency": w.constituency,
            "priority": w.risk_level,
            "signal": primary,
            "risk_score": w.risk_score,
            "status": w.risk_status,
        })
    return alerts
