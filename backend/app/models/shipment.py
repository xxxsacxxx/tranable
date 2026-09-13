"""Order, Shipment, Booking, Container, Package — the operational core (PRD2 s.36, PRD1 s.6/45-46).

Shipment is the central entity everything else hangs off, per PRD1 section 6.
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, JSON, Boolean, DateTime
from sqlalchemy.orm import relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin

SHIPMENT_STAGES = [
    "ORDER_CREATED",
    "BOOKING_REQUESTED",
    "BOOKING_CONFIRMED",
    "DOCUMENTS_PENDING",
    "DOCUMENTS_COMPLETE",
    "EXPORT_CLEARANCE",
    "CARGO_PICKED_UP",
    "IN_TRANSIT",
    "ARRIVED_DESTINATION",
    "IMPORT_CLEARANCE",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "POD_RECEIVED",
    "BILLED",
    "CLOSED",
]


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    quote_id = Column(Integer, ForeignKey("quotes.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    status = Column(String(20), default="OPEN")

    quote = relationship("Quote")
    customer = relationship("Customer")
    shipment = relationship("Shipment", back_populates="order", uselist=False)


class Shipment(Base, TimestampMixin):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    carrier_id = Column(Integer, ForeignKey("carriers.id"), nullable=True)

    origin_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    destination_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    mode = Column(String(20))
    equipment = Column(String(20))
    incoterm = Column(String(10))

    stage = Column(String(30), nullable=False, default="ORDER_CREATED")
    risk_level = Column(String(20), default="LOW")  # LOW|MEDIUM|HIGH|CRITICAL
    is_at_risk = Column(Boolean, default=False)

    planned_departure = Column(String(10))
    actual_departure = Column(String(10))
    planned_arrival = Column(String(10))
    actual_arrival = Column(String(10))

    booking_reference = Column(String(40))
    vessel_or_flight = Column(String(80))
    voyage_number = Column(String(40))
    cutoff_date = Column(String(10))
    document_cutoff_date = Column(String(10))

    order = relationship("Order", back_populates="shipment")
    customer = relationship("Customer")
    carrier = relationship("Carrier")
    origin = relationship("Location", foreign_keys=[origin_location_id])
    destination = relationship("Location", foreign_keys=[destination_location_id])
    containers = relationship("Container", back_populates="shipment", cascade="all, delete-orphan")
    events = relationship(
        "ShipmentEvent", back_populates="shipment", cascade="all, delete-orphan",
        order_by="ShipmentEvent.event_datetime",
    )
    documents = relationship("Document", back_populates="shipment", cascade="all, delete-orphan")
    exceptions = relationship("Exception_", back_populates="shipment", cascade="all, delete-orphan")
    communications = relationship("Communication", back_populates="shipment", cascade="all, delete-orphan")


class Container(Base, TimestampMixin):
    __tablename__ = "containers"

    id = Column(Integer, primary_key=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False)
    container_number = Column(String(20))
    container_type = Column(String(20))
    seal_number = Column(String(20))
    weight_kg = Column(Float)

    discharge_datetime = Column(DateTime, nullable=True)
    pickup_datetime = Column(DateTime, nullable=True)
    return_datetime = Column(DateTime, nullable=True)
    terminal = Column(String(120))

    free_days = Column(Integer, default=7)
    last_free_day = Column(DateTime, nullable=True)
    status = Column(String(30), default="BOOKED")

    shipment = relationship("Shipment", back_populates="containers")
