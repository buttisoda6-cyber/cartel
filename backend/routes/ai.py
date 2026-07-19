"""AI Chat API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from database import get_db
from app_db import get_app_db
from app_models import AIConversation
from schemas import ProductResponse
from services.ai_service import ask_ai, generate_brief, run_sql_agent
from routes.products import get_products_base, attach_ai_predictions

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    context_snapshot: str
    intent: Optional[str] = None
    report_type: Optional[str] = None
    generated_at: Optional[str] = None


class BriefResponse(BaseModel):
    title: str
    answer: str
    context_snapshot: str
    report_type: Optional[str] = None
    generated_at: Optional[str] = None


class SQLAgentRequest(BaseModel):
    question: str


class SQLAgentResponse(BaseModel):
    source_db: Optional[str] = None
    sql: Optional[str] = None
    explanation: Optional[str] = None
    limit_applied: Optional[bool] = None
    generated_at: Optional[str] = None
    summary: Optional[dict] = None
    rows: Optional[list[dict]] = None
    error: Optional[str] = None


class HistoryResponse(BaseModel):
    id: int
    user_query: str
    ai_response: str
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/products", response_model=List[ProductResponse])
def list_ai_products(
    category: Optional[str] = None,
    skip: int = 0,
    db: Session = Depends(get_db),
    app_db: Session = Depends(get_app_db),
):
    """ML-enriched product list — only endpoint that bulk-loads forecast tables."""
    products = get_products_base(db, category=category, skip=skip)
    return attach_ai_predictions(products, app_db)


@router.get("/analytics/inventory-health")
def ai_inventory_health(db: Session = Depends(get_db), app_db: Session = Depends(get_app_db)):
    """ML-based store inventory health score (SQLite). Not used by the main analytics dashboard."""
    from routes.products import attach_ai_predictions, get_products_base

    products = attach_ai_predictions(get_products_base(db), app_db)
    scores = [p.healthScore for p in products if p.healthScore is not None]
    if not scores:
        return {"inventoryHealthScore": 0.0, "productCount": 0}
    return {
        "inventoryHealthScore": round(sum(scores) / len(scores), 1),
        "productCount": len(scores),
    }


@router.post("/chat", response_model=ChatResponse)
def ai_chat(request: ChatRequest, db: Session = Depends(get_db), app_db: Session = Depends(get_app_db)):
    """Ask the AI Store Employee a question."""
    if not request.question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Call AI Service
    result = ask_ai(request.question, db, app_db)

    # Save to history
    conversation = AIConversation(
        user_query=request.question,
        ai_response=result["answer"],
        context_snapshot=result["context_snapshot"]
    )
    app_db.add(conversation)
    app_db.commit()

    return ChatResponse(
        answer=result["answer"],
        context_snapshot=result["context_snapshot"],
        intent=result.get("intent"),
        report_type=result.get("report_type"),
        generated_at=result.get("generated_at"),
    )


@router.get("/history", response_model=List[HistoryResponse])
def get_chat_history(limit: int = 50, app_db: Session = Depends(get_app_db)):
    """Retrieve chat history."""
    history = app_db.query(AIConversation).order_by(AIConversation.created_at.desc()).limit(limit).all()
    # Reverse to get chronological order for chat UI
    return history[::-1]


@router.get("/morning-brief", response_model=BriefResponse)
def morning_brief(db: Session = Depends(get_db), app_db: Session = Depends(get_app_db)):
    """Generate the merchant's morning brief."""
    result = generate_brief("morning", db, app_db)
    return BriefResponse(
        title="Morning Brief",
        answer=result["answer"],
        context_snapshot=result["context_snapshot"],
        report_type=result.get("report_type"),
        generated_at=result.get("generated_at"),
    )


@router.get("/end-of-day", response_model=BriefResponse)
def end_of_day_brief(db: Session = Depends(get_db), app_db: Session = Depends(get_app_db)):
    """Generate the merchant's end-of-day review."""
    result = generate_brief("end_of_day", db, app_db)
    return BriefResponse(
        title="End-of-Day Review",
        answer=result["answer"],
        context_snapshot=result["context_snapshot"],
        report_type=result.get("report_type"),
        generated_at=result.get("generated_at"),
    )


@router.post("/sql", response_model=SQLAgentResponse)
def sql_agent(request: SQLAgentRequest, db: Session = Depends(get_db), app_db: Session = Depends(get_app_db)):
    """Generate and execute a safe read-only SQL query."""
    if not request.question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    result = run_sql_agent(request.question, db, app_db)
    return SQLAgentResponse(**result)
