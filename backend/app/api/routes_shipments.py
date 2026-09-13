from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.agents.order_agent import OrderAgent
from app.api.schemas import AddShipmentEventRequest
from app.api.serializers import serialize_shipment, serialize_task, serialize_exception, serialize_ai_decision
from app.models.shipment import Shipment
from app.models.events import Task, Exception_
from app.models.audit import AIDecision

router = APIRouter(prefix="/shipments", tags=["shipments"])


@router.get("")
def list_shipments(db: Session = Depends(get_db)):
    shipments = db.query(Shipment).order_by(Shipment.id.desc()).all()
    return [serialize_shipment(s) for s in shipments]


@router.get("/{shipment_id}")
def get_shipment(shipment_id: int, db: Session = Depends(get_db)):
    shipment = db.query(Shipment).get(shipment_id)
    if not shipment:
        raise HTTPException(404, "Shipment not found")
    data = serialize_shipment(shipment, detailed=True)
    tasks = db.query(Task).filter_by(shipment_id=shipment.id).order_by(Task.id).all()
    data["tasks"] = [serialize_task(t) for t in tasks]
    decisions = db.query(AIDecision).filter_by(entity_type="shipment", entity_id=shipment.id).order_by(AIDecision.id).all()
    data["ai_decisions"] = [serialize_ai_decision(d) for d in decisions]
    return data


@router.post("/{shipment_id}/events")
def add_event(shipment_id: int, payload: AddShipmentEventRequest, db: Session = Depends(get_db)):
    agent = OrderAgent(db)
    try:
        agent.add_shipment_event(shipment_id, payload.event_type, location=payload.location, notes=payload.notes)
    except ValueError as e:
        raise HTTPException(400, str(e))
    shipment = db.query(Shipment).get(shipment_id)
    return serialize_shipment(shipment, detailed=True)


@router.get("/{shipment_id}/exceptions")
def get_shipment_exceptions(shipment_id: int, db: Session = Depends(get_db)):
    exceptions = db.query(Exception_).filter_by(shipment_id=shipment_id).all()
    return [serialize_exception(e) for e in exceptions]
