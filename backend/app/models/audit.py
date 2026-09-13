"""AuditLog + AIDecision — auditability layer per PRD1 s.51-52 / PRD2 s.40, and the
"Audit log" + "Precedent / Case history" boxes in the architecture diagram.
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, JSON, DateTime, Boolean
import datetime

from app.core.db import Base
from app.models.mixins import TimestampMixin


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    entity_type = Column(String(30), nullable=False)  # quote|order|shipment|document|exception
    entity_id = Column(Integer, nullable=False)
    action = Column(String(60), nullable=False)  # e.g. STAGE_CHANGED, QUOTE_APPROVED
    actor = Column(String(60), default="system")  # system|ai|user email
    from_value = Column(String(60))
    to_value = Column(String(60))
    details = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class AIDecision(Base, TimestampMixin):
    """One record per AI Gateway call — the "full decision audit" cross-cutting requirement
    from the architecture diagram's Control & Governance column.
    """

    __tablename__ = "ai_decisions"

    id = Column(Integer, primary_key=True)
    entity_type = Column(String(30), nullable=False)
    entity_id = Column(Integer, nullable=False)
    task = Column(String(60), nullable=False)  # shipment_extraction|hs_classification|root_cause|...
    model = Column(String(60), default="stub-heuristic-v1")
    prompt_version = Column(String(20), default="v1")
    input_context = Column(JSON, default=dict)
    decision = Column(JSON, default=dict)
    confidence = Column(Float)
    evidence = Column(JSON, default=list)
    facts = Column(JSON, default=list)
    inferences = Column(JSON, default=list)
    recommended_action = Column(Text)
    human_override = Column(Boolean, default=False)
    final_decision = Column(JSON, default=dict)
    reviewed_by = Column(String(120))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
