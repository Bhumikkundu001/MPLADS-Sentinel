import json
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Work(Base):
    __tablename__ = "works"

    # Identity
    id = Column(String(30), primary_key=True)           # MPL-2026-00125
    name = Column(String(300), nullable=False)
    description = Column(Text)
    house = Column(String(20), index=True)               # Lok Sabha / Rajya Sabha
    mp_name = Column(String(100))
    state = Column(String(80), index=True)
    constituency = Column(String(100))
    district = Column(String(100))
    category = Column(String(80))                        # Road, School, Water, etc.
    executing_agency = Column(String(150))
    status = Column(String(50), index=True)               # Completed, In Progress, Delayed, Stalled

    # Financial (in INR lakhs)
    recommended_amount = Column(Float)
    sanctioned_amount = Column(Float)
    expenditure = Column(Float)

    # Timeline
    proposed_date = Column(String(20))
    expected_completion = Column(String(20))
    actual_completion = Column(String(20))
    progress = Column(Integer)                           # 0-100; NULL = not available for this row

    # ML outputs
    risk_score = Column(Integer, default=0)              # 0-100
    risk_level = Column(String(10), default="Low", index=True)   # High / Medium / Low
    risk_status = Column(String(50), default="Normal", index=True)  # Requires Review / Normal
    anomaly_score = Column(Float, default=0.0)           # Isolation Forest score (lower = more anomalous)
    is_anomaly = Column(Boolean, default=False, index=True)
    risk_indicators_json = Column(Text, default="[]")    # JSON list of indicator objects
    risk_computed_at = Column(DateTime, nullable=True)   # NULL = not yet scored

    # Source / provenance (real-dataset migration)
    data_source = Column(String(30), default="demo_seed", index=True)  # demo_seed / lok_sabha_real / rajya_sabha_real
    source_row_id = Column(String(30), nullable=True)    # original CSV sr_no, for traceability
    dataset_version = Column(String(60), nullable=True)  # e.g. lok_sabha_final_processed_ml_master_v1
    raw_status = Column(String(100), nullable=True)      # verbatim original work_status text
    is_reported_complete = Column(Boolean, nullable=True)  # direct copy of source `completed` flag

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    similarities_as_source = relationship(
        "WorkSimilarity",
        foreign_keys="WorkSimilarity.work_id",
        back_populates="work",
        cascade="all, delete-orphan",
    )

    @property
    def risk_indicators(self):
        try:
            return json.loads(self.risk_indicators_json or "[]")
        except Exception:
            return []

    @property
    def cost_deviation_pct(self):
        if self.sanctioned_amount and self.sanctioned_amount > 0:
            return round(
                ((self.expenditure or 0) - self.sanctioned_amount)
                / self.sanctioned_amount
                * 100,
                1,
            )
        return 0.0

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "house": self.house,
            "mp_name": self.mp_name,
            "state": self.state,
            "constituency": self.constituency,
            "district": self.district,
            "category": self.category,
            "executing_agency": self.executing_agency,
            "status": self.status,
            "recommended_amount": self.recommended_amount,
            "sanctioned_amount": self.sanctioned_amount,
            "expenditure": self.expenditure,
            "proposed_date": self.proposed_date,
            "expected_completion": self.expected_completion,
            "actual_completion": self.actual_completion,
            "progress": self.progress,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "risk_status": self.risk_status,
            "anomaly_score": self.anomaly_score,
            "is_anomaly": self.is_anomaly,
            "risk_indicators": self.risk_indicators,
            "cost_deviation_pct": self.cost_deviation_pct,
        }


class WorkSimilarity(Base):
    __tablename__ = "work_similarities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    work_id = Column(String(30), ForeignKey("works.id", ondelete="CASCADE"), index=True)
    similar_work_id = Column(String(30), ForeignKey("works.id", ondelete="CASCADE"))
    similarity_score = Column(Float)                     # 0.0 – 1.0

    work = relationship("Work", foreign_keys=[work_id], back_populates="similarities_as_source")
    similar_work = relationship("Work", foreign_keys=[similar_work_id])

    def to_dict(self):
        sw = self.similar_work
        return {
            "id": sw.id,
            "name": sw.name,
            "state": sw.state,
            "constituency": sw.constituency,
            "district": sw.district,
            "category": sw.category,
            "risk_score": sw.risk_score,
            "risk_level": sw.risk_level,
            "status": sw.status,
            "similarity_score": round(self.similarity_score * 100, 1),
        }
