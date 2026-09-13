from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import copilot_service

router = APIRouter()


class CopilotRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: str | None = None
    house: str | None = Field(
        None, description="Global monitoring context: 'Lok Sabha', 'Rajya Sabha', or omitted/null for all houses"
    )


class CopilotResponse(BaseModel):
    answer: str
    intent: str
    confidence: float
    sources: list[dict]
    data: dict
    suggested_questions: list[str]


@router.post("", response_model=CopilotResponse)
async def ask_copilot(request: CopilotRequest, db: Session = Depends(get_db)):
    try:
        result = copilot_service.process_query(request.message, db, house=request.house)
        return result
    except Exception as e:
        raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Copilot service error. Please try again.",
    )
