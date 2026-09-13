from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.agents.order_agent import OrderAgent
from app.api.schemas import CreateQuoteRequest, ApproveQuoteRequest
from app.api.serializers import serialize_quote, serialize_communication, serialize_shipment, serialize_task, serialize_ai_decision
from app.models.quote import Quote
from app.models.events import Communication, Task
from app.models.audit import AIDecision

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.get("")
def list_quotes(db: Session = Depends(get_db)):
    quotes = db.query(Quote).order_by(Quote.id.desc()).all()
    return [serialize_quote(q) for q in quotes]


@router.post("")
def create_quote(payload: CreateQuoteRequest, db: Session = Depends(get_db)):
    agent = OrderAgent(db)
    quote = agent.create_quote_from_text(payload.raw_text, customer_id=payload.customer_id, source=payload.source)
    return serialize_quote(quote, detailed=True)


@router.get("/{quote_id}")
def get_quote(quote_id: int, db: Session = Depends(get_db)):
    quote = db.query(Quote).get(quote_id)
    if not quote:
        raise HTTPException(404, "Quote not found")
    data = serialize_quote(quote, detailed=True)
    comms = db.query(Communication).filter_by(quote_id=quote.id).order_by(Communication.id).all()
    data["communications"] = [serialize_communication(c) for c in comms]
    tasks = db.query(Task).filter_by(quote_id=quote.id).order_by(Task.id).all()
    data["tasks"] = [serialize_task(t) for t in tasks]
    decisions = db.query(AIDecision).filter_by(entity_type="quote", entity_id=quote.id).order_by(AIDecision.id).all()
    data["ai_decisions"] = [serialize_ai_decision(d) for d in decisions]
    return data


@router.post("/{quote_id}/approve")
def approve_quote(quote_id: int, payload: ApproveQuoteRequest, db: Session = Depends(get_db)):
    agent = OrderAgent(db)
    try:
        shipment = agent.approve_quote(quote_id, payload.option_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return serialize_shipment(shipment, detailed=True)
