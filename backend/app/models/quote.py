"""Quote / QuoteRequirement per PRD2 sections 7-19.

A Quote carries the "QuoteRequirement" extraction object (known / inferred / missing fields),
one or more QuoteOptions (cheapest / fastest / recommended per PRD2 section 16), and once
approved converts 1:1 into an Order.
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin

QUOTE_STATUSES = [
    "DRAFT",  # extraction just ran
    "MISSING_INFO",  # required fields missing, waiting on customer
    "QUOTED",  # options calculated, quote sent
    "APPROVED",  # customer accepted an option
    "EXPIRED",
    "REJECTED",
]


class Quote(Base, TimestampMixin):
    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    status = Column(String(20), nullable=False, default="DRAFT")

    # raw customer request, as received (email / portal / pasted text)
    raw_request_text = Column(Text, nullable=False)
    raw_request_source = Column(String(30), default="email")

    # --- QuoteRequirement extraction object (PRD2 section 8) ---
    origin_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    destination_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    # OD normalization (PRD2 s.12): origin/destination above are the stated city; these are the
    # resolved port/airport gateway used for rate lookup — e.g. origin=Foshan, origin_port=Yantian.
    origin_port_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    destination_port_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    pickup_address = Column(String(250))
    delivery_address = Column(String(250))
    cargo_description = Column(Text)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    hs_code_candidate = Column(String(12))
    quantity = Column(Integer)
    package_type = Column(String(40))
    weight_kg = Column(Float)
    volume_cbm = Column(Float)
    equipment = Column(String(20))  # 20GP|40GP|40HC|LCL|AIR
    mode = Column(String(20))  # ocean_fcl|ocean_lcl|air|road
    service_type = Column(String(30))  # door-to-door|port-to-port|door-to-port etc
    incoterm = Column(String(10))
    cargo_value = Column(Float)
    currency = Column(String(3), default="USD")
    ready_date = Column(String(10))
    required_delivery_date = Column(String(10))
    dangerous_goods = Column(Boolean, default=False)
    temperature_control = Column(Boolean, default=False)
    insurance_required = Column(Boolean, default=False)
    customs_clearance_required = Column(Boolean, default=True)
    special_handling = Column(String(250))

    extraction_confidence = Column(Float)
    known_fields = Column(JSON, default=list)
    inferred_fields = Column(JSON, default=list)
    missing_fields = Column(JSON, default=list)

    hs_candidates_json = Column(JSON, default=list)  # [{"code":..,"description":..,"confidence":..}]

    origin = relationship("Location", foreign_keys=[origin_location_id])
    destination = relationship("Location", foreign_keys=[destination_location_id])
    origin_port = relationship("Location", foreign_keys=[origin_port_location_id])
    destination_port = relationship("Location", foreign_keys=[destination_port_location_id])
    product = relationship("Product")
    customer = relationship("Customer")
    approved_option_id = Column(Integer, ForeignKey("quote_options.id", use_alter=True, name="fk_quote_approved_option"), nullable=True)

    options = relationship("QuoteOption", back_populates="quote", cascade="all, delete-orphan", foreign_keys="QuoteOption.quote_id")


class QuoteOption(Base, TimestampMixin):
    """One priced option (Cheapest / Fastest / Recommended...) per PRD2 section 16."""

    __tablename__ = "quote_options"

    id = Column(Integer, primary_key=True)
    quote_id = Column(Integer, ForeignKey("quotes.id"), nullable=False)
    label = Column(String(30), nullable=False)  # Cheapest|Fastest|Best Reliability|Recommended
    carrier_id = Column(Integer, ForeignKey("carriers.id"), nullable=True)
    rate_card_id = Column(Integer, ForeignKey("rate_cards.id"), nullable=True)
    transit_days = Column(Integer)
    reliability_score = Column(Float)

    base_freight = Column(Float, default=0)
    origin_charges = Column(Float, default=0)
    destination_charges = Column(Float, default=0)
    customs_charges = Column(Float, default=0)
    trucking_charges = Column(Float, default=0)
    documentation_charges = Column(Float, default=0)
    surcharges = Column(Float, default=0)
    insurance = Column(Float, default=0)
    risk_contingency = Column(Float, default=0)
    total_cost = Column(Float, default=0)
    margin = Column(Float, default=0)
    customer_price = Column(Float, default=0)
    currency = Column(String(3), default="USD")

    win_probability = Column(Float)
    is_recommended = Column(Boolean, default=False)

    quote = relationship("Quote", back_populates="options", foreign_keys=[quote_id])
    carrier = relationship("Carrier")
    rate_card = relationship("RateCard")
