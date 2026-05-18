"""
Mode 1 – AI coworker chat endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat_service import run_chat

router = APIRouter(prefix="/chat", tags=["Chat – AI Coworker"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Send a natural language query to the AI coworker.
    The agent will query the CMMS, standards, and manuals as needed.
    """
    return run_chat(request, db)
