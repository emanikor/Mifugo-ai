"""
Chat endpoint consumed by the React chat UI. Requires auth like everything
else — this is internal market intelligence, not a public tool.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Agent
from app.rag.pipeline import answer_question
from app.schemas import ChatRequest, ChatResponse
from app.security import get_current_agent

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    return answer_question(db, payload.question)
