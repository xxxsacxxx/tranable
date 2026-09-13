"""Document checklist & validation, per PRD2 sections 21-23."""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin

DOCUMENT_TYPES = [
    "COMMERCIAL_INVOICE",
    "PACKING_LIST",
    "CERTIFICATE_OF_ORIGIN",
    "EXPORT_DECLARATION",
    "IMPORT_DECLARATION",
    "BL_INSTRUCTIONS",
    "BILL_OF_LADING",
    "INSURANCE_CERTIFICATE",
    "DG_DECLARATION",
    "IMPORT_LICENSE",
    "PHYTOSANITARY_CERTIFICATE",
    "HEALTH_CERTIFICATE",
    "ARRIVAL_NOTICE",
    "DELIVERY_ORDER",
    "PROOF_OF_DELIVERY",
]


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False)
    document_type = Column(String(40), nullable=False)
    requirement_level = Column(String(20), default="REQUIRED")  # REQUIRED|CONDITIONAL|OPTIONAL
    status = Column(String(20), default="MISSING")  # MISSING|RECEIVED|VALIDATED|REJECTED
    file_name = Column(String(200))
    extracted_fields = Column(JSON, default=dict)
    validation_notes = Column(Text)

    shipment = relationship("Shipment", back_populates="documents")
