"""Builds the dynamic per-shipment document checklist — PRD2 s.21.

    Checklist = f(Product + HS + Origin + Destination + Mode + Incoterm + Customer + Regulatory Rules)

Base documents are always required; everything else comes from the deterministic
TradeRule lookup performed via the AI Gateway's `trade_rule_analysis` task (that task is
itself 100%-deterministic — it's registered on the gateway so every requirement lookup goes
through one auditable interface, per PRD1 s.57).
"""
from sqlalchemy.orm import Session

from app.brain.ai_gateway.gateway import AIGateway
from app.models.documents import Document
from app.models.shipment import Shipment

BASE_REQUIRED_DOCS = [
    ("COMMERCIAL_INVOICE", "Commercial Invoice"),
    ("PACKING_LIST", "Packing List"),
    ("BL_INSTRUCTIONS", "B/L Instructions"),
]

REQUIREMENT_TEXT_TO_DOC_TYPE = {
    "certificate of origin": "CERTIFICATE_OF_ORIGIN",
    "commercial invoice": "COMMERCIAL_INVOICE",
    "packing list": "PACKING_LIST",
    "import declaration": "IMPORT_DECLARATION",
    "export declaration": "EXPORT_DECLARATION",
    "isf (10+2) filing": "IMPORT_DECLARATION",
    "conformity certificate for steel goods (esma)": "IMPORT_LICENSE",
}


def build_document_checklist(db: Session, shipment: Shipment, hs_code: str | None) -> list[Document]:
    gateway = AIGateway(db)
    destination_country_id = shipment.destination.country_id if shipment.destination else None

    result = gateway.generate(
        "trade_rule_analysis",
        context={
            "destination_country_id": destination_country_id,
            "hs_code": hs_code,
            "direction": "import",
        },
        entity_type="shipment",
        entity_id=shipment.id,
    )

    docs: list[Document] = []
    seen_types = set()

    for doc_type, label in BASE_REQUIRED_DOCS:
        docs.append(Document(shipment_id=shipment.id, document_type=doc_type, requirement_level="REQUIRED"))
        seen_types.add(doc_type)

    for req in result.decision.get("requirements", []):
        doc_type = REQUIREMENT_TEXT_TO_DOC_TYPE.get(req["requirement"].lower())
        if not doc_type:
            # requirement doesn't map to a document artifact (e.g. a pure duty/tax note) — skip
            continue
        if doc_type in seen_types:
            continue
        seen_types.add(doc_type)
        level = "REQUIRED" if req["severity"] == "required" else "CONDITIONAL" if req["severity"] == "conditional" else "OPTIONAL"
        docs.append(Document(shipment_id=shipment.id, document_type=doc_type, requirement_level=level,
                              validation_notes=f"Required by {req.get('authority', 'destination customs')} ({req.get('source', 'trade rule')})"))

    db.add_all(docs)
    db.flush()
    return docs
