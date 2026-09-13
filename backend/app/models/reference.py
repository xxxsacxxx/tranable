"""Reference / trade-lane data: countries, locations, ports, carriers, product & HS ontology.

Maps to PRD2 sections 9-13, 32-34 (Product/HS intelligence, OD matrix, trade lane graph)
and to the "Reference data" box of the Data Foundation layer in the architecture diagram.
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin


class Country(Base, TimestampMixin):
    __tablename__ = "countries"

    id = Column(Integer, primary_key=True)
    iso2 = Column(String(2), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    region = Column(String(60))


class Location(Base, TimestampMixin):
    """A city / place that can host ports, airports, warehouses, or be a pickup/delivery address."""

    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)
    location_type = Column(String(30), nullable=False, default="city")  # city|port|airport|warehouse
    unlocode = Column(String(10))
    latitude = Column(Float)
    longitude = Column(Float)

    country = relationship("Country")


class Carrier(Base, TimestampMixin):
    __tablename__ = "carriers"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    scac = Column(String(10))
    mode = Column(String(20), nullable=False, default="ocean")  # ocean|air|road|rail
    reliability_score = Column(Float, default=0.9)


class Service(Base, TimestampMixin):
    """A carrier's service on a lane (used for rate lookup and routing recommendation)."""

    __tablename__ = "services"

    id = Column(Integer, primary_key=True)
    carrier_id = Column(Integer, ForeignKey("carriers.id"), nullable=False)
    origin_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    destination_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    mode = Column(String(20), nullable=False, default="ocean")
    transit_days = Column(Integer, nullable=False)
    frequency_per_week = Column(Float, default=1.0)

    carrier = relationship("Carrier")
    origin = relationship("Location", foreign_keys=[origin_location_id])
    destination = relationship("Location", foreign_keys=[destination_location_id])


class HSCode(Base, TimestampMixin):
    """International HS hierarchy: chapter -> heading -> subheading, per PRD2 section 10."""

    __tablename__ = "hs_codes"

    id = Column(Integer, primary_key=True)
    code = Column(String(12), unique=True, nullable=False)  # e.g. 731812 (heading/subheading)
    level = Column(String(20), nullable=False)  # chapter|heading|subheading
    description = Column(Text, nullable=False)
    parent_code = Column(String(12), ForeignKey("hs_codes.code"), nullable=True)
    dangerous_goods_flag = Column(Boolean, default=False)

    parent = relationship("HSCode", remote_side=[code])


class Product(Base, TimestampMixin):
    """Customer product master, per PRD2 section 37. hs_candidates/confirmed_hs link into HSCode."""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    sku = Column(String(60))
    description = Column(Text, nullable=False)
    manufacturer = Column(String(150))
    category = Column(String(80))
    attributes = Column(JSON, default=dict)
    country_of_origin_id = Column(Integer, ForeignKey("countries.id"), nullable=True)
    confirmed_hs_code = Column(String(12), ForeignKey("hs_codes.code"), nullable=True)
    dangerous_goods = Column(Boolean, default=False)
    regulatory_flags = Column(JSON, default=list)

    customer = relationship("Customer", back_populates="products")
    country_of_origin = relationship("Country")
    confirmed_hs = relationship("HSCode")


class TradeRule(Base, TimestampMixin):
    """Configurable regulatory/document-requirement rule, per PRD2 section 32.

    Deliberately data-driven rather than hard-coded IF/THEN in application code.
    """

    __tablename__ = "trade_rules"

    id = Column(Integer, primary_key=True)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=True)
    direction = Column(String(10), nullable=True)  # import|export|None(both)
    hs_scope = Column(String(12), nullable=True)  # HS code / chapter prefix this rule applies to; null = all
    mode = Column(String(20), nullable=True)
    requirement_type = Column(String(40), nullable=False)  # document|license|prohibition|duty_note
    requirement = Column(String(200), nullable=False)
    severity = Column(String(20), nullable=False, default="required")  # required|conditional|optional
    authority = Column(String(120))
    source = Column(String(200))

    country = relationship("Country")


class RateCard(Base, TimestampMixin):
    """A carrier's contracted or tariff rate for a lane/equipment/effective period, per PRD1 section 13."""

    __tablename__ = "rate_cards"

    id = Column(Integer, primary_key=True)
    carrier_id = Column(Integer, ForeignKey("carriers.id"), nullable=False)
    origin_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    destination_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    mode = Column(String(20), nullable=False, default="ocean")
    equipment = Column(String(20))  # 20GP|40GP|40HC|LCL|AIR_KG etc
    effective_from = Column(String(10))
    effective_to = Column(String(10))

    base_freight = Column(Float, nullable=False)
    documentation_fee = Column(Float, default=0)
    origin_handling_fee = Column(Float, default=0)
    destination_handling_fee = Column(Float, default=0)
    fuel_surcharge_pct = Column(Float, default=0)
    currency = Column(String(3), default="USD")

    free_time_days = Column(Integer, default=7)
    demurrage_tier_json = Column(JSON, default=list)  # [{"from_day":1,"to_day":3,"rate":100}, ...]

    carrier = relationship("Carrier")
    origin = relationship("Location", foreign_keys=[origin_location_id])
    destination = relationship("Location", foreign_keys=[destination_location_id])
