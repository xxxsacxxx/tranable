"""ShipmentEvent (event-sourced timeline), Exception, Communication, Task.

Per PRD1 s.47 and PRD2 s.27-28: use an event model rather than hard-coded date fields,
and run an exception-first operating model.
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, JSON, DateTime
from sqlalchemy.orm import relationship
import datetime

from app.core.db import Base
from app.models.mixins import TimestampMixin

EVENT_TYPES = [
    "QUOTE_REQUESTED", "QUOTE_CREATED", "QUOTE_SENT", "QUOTE_ACCEPTED",
    "ORDER_CREATED", "BOOKING_REQUESTED", "BOOKING_CONFIRMED",
    "DOCUMENTS_REQUESTED", "DOCUMENTS_RECEIVED", "CARGO_READY",
    "PICKUP_REQUESTED", "PICKED_UP", "RECEIVED_AT_WAREHOUSE",
    "CUSTOMS_FILED", "CUSTOMS_CLEARED", "LOADED", "DEPARTED",
    "TRANSSHIPMENT", "ARRIVED", "DISCHARGED", "DELIVERY_ORDER_RELEASED",
    "OUT_FOR_DELIVERY", "DELIVERED", "POD_RECEIVED", "BILLED", "CLOSED",
]


class ShipmentEvent(Base, TimestampMixin):
    __tablename__ = "shipment_events"

    id = Column(Integer, primary_key=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False)
    container_id = Column(Integer, ForeignKey("containers.id"), nullable=True)
    event_type = Column(String(40), nullable=False)
    event_datetime = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    source = Column(String(40), default="manual")  # manual|carrier_api|email|system
    location = Column(String(120))
    notes = Column(Text)

    shipment = relationship("Shipment", back_populates="events")


class Exception_(Base, TimestampMixin):
    """Named Exception_ to avoid clashing with the Python builtin."""

    __tablename__ = "exceptions"

    id = Column(Integer, primary_key=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    quote_id = Column(Integer, ForeignKey("quotes.id"), nullable=True)
    entity_type = Column(String(30), nullable=False)  # quote|shipment|document|customs
    exception_type = Column(String(50), nullable=False)
    severity = Column(String(20), default="MEDIUM")  # LOW|MEDIUM|HIGH|CRITICAL
    status = Column(String(20), default="OPEN")  # OPEN|IN_PROGRESS|RESOLVED
    amount_at_risk = Column(Float)
    confidence = Column(Float)
    reason = Column(Text)
    recommended_action = Column(Text)
    assigned_to = Column(String(120))
    resolved_at = Column(DateTime, nullable=True)

    shipment = relationship("Shipment", back_populates="exceptions")


class Communication(Base, TimestampMixin):
    __tablename__ = "communications"

    id = Column(Integer, primary_key=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    quote_id = Column(Integer, ForeignKey("quotes.id"), nullable=True)
    channel = Column(String(20), default="email")  # email|portal|sms|internal_note
    direction = Column(String(10), default="outbound")  # inbound|outbound
    generated_by = Column(String(20), default="ai")  # ai|human|system
    subject = Column(String(200))
    body = Column(Text, nullable=False)
    trigger_event = Column(String(60))  # e.g. BOOKING_CONFIRMED

    shipment = relationship("Shipment", back_populates="communications")


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    quote_id = Column(Integer, ForeignKey("quotes.id"), nullable=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="OPEN")  # OPEN|IN_PROGRESS|DONE
    owner_role = Column(String(30))  # sales|operations|customs|finance
    due_date = Column(DateTime, nullable=True)
