"""Order Agent — owns the Enquiry-to-Delivery workflow end to end (architecture diagram:
Agentic Layer > Domain Agents > "Order Agent: quote -> booking").

It is a thin orchestrator: every number comes from the deterministic rules engine
(app/brain/rules), every interpretive/generative step goes through the AI Gateway
(app/brain/ai_gateway), and every state transition is written to ShipmentEvent/AuditLog.
The agent itself contains no pricing math and no free-form text generation.
"""
from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from app.brain.ai_gateway.gateway import AIGateway
from app.brain.rules.quote_calc import calculate_quote_options
from app.brain.rules.od_normalization import resolve_gateway
from app.brain.rules.document_checklist import build_document_checklist
from app.models.quote import Quote, QuoteOption
from app.models.shipment import Order, Shipment
from app.models.events import ShipmentEvent, Communication, Task, Exception_
from app.models.audit import AuditLog
from app.models.customer import Customer

ESSENTIAL_FOR_QUOTING = ["origin_location_id", "destination_location_id"]

# event_type -> shipment stage it advances to, per PRD2 s.27
EVENT_STAGE_MAP = {
    "BOOKING_REQUESTED": "BOOKING_REQUESTED",
    "BOOKING_CONFIRMED": "BOOKING_CONFIRMED",
    "DOCUMENTS_RECEIVED": "DOCUMENTS_COMPLETE",
    "CUSTOMS_FILED": "EXPORT_CLEARANCE",
    "PICKED_UP": "CARGO_PICKED_UP",
    "LOADED": "CARGO_PICKED_UP",
    "DEPARTED": "IN_TRANSIT",
    "ARRIVED": "ARRIVED_DESTINATION",
    "DISCHARGED": "ARRIVED_DESTINATION",
    "CUSTOMS_CLEARED": "IMPORT_CLEARANCE",
    "OUT_FOR_DELIVERY": "OUT_FOR_DELIVERY",
    "DELIVERED": "DELIVERED",
    "POD_RECEIVED": "POD_RECEIVED",
    "BILLED": "BILLED",
    "CLOSED": "CLOSED",
}

# milestone events that should trigger a grounded customer communication, per PRD2 s.24
MILESTONE_EMAIL_PURPOSE = {
    "BOOKING_CONFIRMED": "booking_confirmed",
    "DEPARTED": "shipment_update",
    "ARRIVED": "shipment_update",
    "OUT_FOR_DELIVERY": "shipment_update",
    "DELIVERED": "shipment_update",
}


def _audit(db: Session, entity_type: str, entity_id: int, action: str, actor="system", from_value=None, to_value=None, details=None):
    db.add(AuditLog(entity_type=entity_type, entity_id=entity_id, action=action, actor=actor,
                     from_value=from_value, to_value=to_value, details=details or {}))


class OrderAgent:
    def __init__(self, db: Session):
        self.db = db
        self.ai = AIGateway(db)

    # ------------------------------------------------------------------
    def create_quote_from_text(self, raw_text: str, customer_id: int | None = None,
                                source: str = "email") -> Quote:
        from app.models.mixins import make_code
        n = self.db.query(Quote).count() + 1
        quote = Quote(code=make_code("QUO", n), raw_request_text=raw_text, raw_request_source=source,
                      customer_id=customer_id, status="DRAFT")
        self.db.add(quote)
        self.db.flush()

        # --- AI Layer 1/2: extraction ---
        extraction = self.ai.generate("shipment_extraction", {"text": raw_text},
                                       entity_type="quote", entity_id=quote.id)
        fields = extraction.decision["fields"]
        for k, v in fields.items():
            if hasattr(quote, k):
                setattr(quote, k, v)
        quote.extraction_confidence = extraction.confidence
        quote.known_fields = extraction.decision["known_fields"]
        quote.inferred_fields = extraction.decision["inferred_fields"]
        quote.missing_fields = extraction.decision["missing_fields"]

        # --- OD normalization (PRD2 s.12) ---
        if quote.origin_location_id:
            gw = resolve_gateway(self.db, quote.origin_location_id, quote.mode)
            quote.origin_port_location_id = gw.id if gw else None
        if quote.destination_location_id:
            gw = resolve_gateway(self.db, quote.destination_location_id, quote.mode)
            quote.destination_port_location_id = gw.id if gw else None

        # --- AI Layer 3: HS classification ---
        if quote.cargo_description:
            hs_result = self.ai.generate("hs_classification", {"cargo_description": quote.cargo_description},
                                          entity_type="quote", entity_id=quote.id)
            quote.hs_candidates_json = hs_result.decision["hs_candidates"]
            top = hs_result.decision["top_candidate"]
            if top["confidence"] >= 0.5:
                quote.hs_code_candidate = top["code"]

        self.db.flush()
        _audit(self.db, "quote", quote.id, "QUOTE_EXTRACTED", actor="ai",
               details={"confidence": extraction.confidence, "missing_fields": quote.missing_fields})

        essential_missing = [f for f in ESSENTIAL_FOR_QUOTING if not getattr(quote, f)]

        if essential_missing:
            quote.status = "MISSING_INFO"
            self._draft_missing_info_email(quote)
            self._create_task(quote, "Follow up: shipment details missing for quote",
                               f"Need: {', '.join(quote.missing_fields)}", owner_role="sales")
        else:
            self._price_quote(quote)

        self.db.commit()
        self.db.refresh(quote)
        return quote

    # ------------------------------------------------------------------
    def _price_quote(self, quote: Quote):
        priced = calculate_quote_options(self.db, quote)
        if not priced:
            quote.status = "MISSING_INFO"
            exc = Exception_(quote_id=quote.id, entity_type="quote", exception_type="NO_RATE_AVAILABLE",
                              severity="MEDIUM", reason="No rate card found for this origin/destination/equipment combination.",
                              recommended_action="Request a spot rate from a carrier or add a rate card for this lane.")
            self.db.add(exc)
            _audit(self.db, "quote", quote.id, "NO_RATE_FOUND", actor="system")
            return

        for p in priced:
            opt = QuoteOption(
                quote_id=quote.id, label=p.label, carrier_id=p.carrier_id, rate_card_id=p.rate_card_id,
                transit_days=p.transit_days, reliability_score=p.reliability_score,
                base_freight=p.base_freight, origin_charges=p.origin_charges,
                destination_charges=p.destination_charges, customs_charges=p.customs_charges,
                trucking_charges=p.trucking_charges, documentation_charges=p.documentation_charges,
                surcharges=p.surcharges, insurance=p.insurance, risk_contingency=p.risk_contingency,
                total_cost=p.total_cost, margin=p.margin, customer_price=p.customer_price,
                currency=p.currency, win_probability=p.win_probability, is_recommended=p.is_recommended,
            )
            self.db.add(opt)
        quote.status = "QUOTED"
        self.db.flush()
        _audit(self.db, "quote", quote.id, "QUOTE_PRICED", actor="system",
               details={"options": [p.label for p in priced]})
        self._draft_quote_email(quote)

    # ------------------------------------------------------------------
    def _draft_missing_info_email(self, quote: Quote):
        result = self.ai.generate("customer_email", {
            "purpose": "missing_information", "reference": quote.code,
            "missing_fields": quote.missing_fields,
        }, entity_type="quote", entity_id=quote.id)
        self.db.add(Communication(quote_id=quote.id, channel="email", direction="outbound",
                                   generated_by="ai", subject=result.decision["subject"],
                                   body=result.decision["body"], trigger_event="MISSING_INFO_DETECTED"))

    def _draft_quote_email(self, quote: Quote):
        recommended = next((o for o in quote.options if o.is_recommended), quote.options[0])
        result = self.ai.generate("customer_email", {
            "purpose": "quote_sent", "reference": quote.code,
            "origin": quote.origin.name if quote.origin else "", "destination": quote.destination.name if quote.destination else "",
            "mode": quote.mode, "equipment": quote.equipment, "service_type": quote.service_type,
            "customs_clearance_required": quote.customs_clearance_required,
            "recommended_option": {"label": recommended.label, "currency": recommended.currency,
                                    "customer_price": round(recommended.customer_price, 2),
                                    "transit_days": recommended.transit_days},
        }, entity_type="quote", entity_id=quote.id)
        self.db.add(Communication(quote_id=quote.id, channel="email", direction="outbound",
                                   generated_by="ai", subject=result.decision["subject"],
                                   body=result.decision["body"], trigger_event="QUOTE_SENT"))
        self.db.flush()

    def _create_task(self, quote: Quote | None, title: str, description: str, owner_role: str,
                      shipment_id: int | None = None):
        self.db.add(Task(quote_id=quote.id if quote else None, shipment_id=shipment_id, title=title,
                          description=description, owner_role=owner_role))

    # ------------------------------------------------------------------
    def approve_quote(self, quote_id: int, option_id: int) -> Shipment:
        from app.models.mixins import make_code
        quote = self.db.query(Quote).get(quote_id)
        option = self.db.query(QuoteOption).get(option_id)
        if not quote or not option or option.quote_id != quote.id:
            raise ValueError("Invalid quote/option")

        quote.status = "APPROVED"
        quote.approved_option_id = option.id
        _audit(self.db, "quote", quote.id, "QUOTE_APPROVED", actor="customer",
               details={"option": option.label, "customer_price": option.customer_price})

        order = Order(code=make_code("ORD", self.db.query(Order).count() + 1),
                      quote_id=quote.id, customer_id=quote.customer_id, status="OPEN")
        self.db.add(order)
        self.db.flush()

        shipment = Shipment(
            code=make_code("SHP", self.db.query(Shipment).count() + 1),
            order_id=order.id, customer_id=quote.customer_id, carrier_id=option.carrier_id,
            origin_location_id=quote.origin_location_id, destination_location_id=quote.destination_location_id,
            mode=quote.mode, equipment=quote.equipment, incoterm=quote.incoterm,
            stage="ORDER_CREATED",
        )
        self.db.add(shipment)
        self.db.flush()

        self.db.add(ShipmentEvent(shipment_id=shipment.id, event_type="QUOTE_ACCEPTED", source="system"))
        self.db.add(ShipmentEvent(shipment_id=shipment.id, event_type="ORDER_CREATED", source="system"))
        _audit(self.db, "shipment", shipment.id, "SHIPMENT_CREATED", actor="system",
               details={"from_quote": quote.code})

        # dynamic document checklist (PRD2 s.21-22)
        build_document_checklist(self.db, shipment, quote.hs_code_candidate)

        self._create_task(quote, f"Request booking with {option.carrier_id and option.carrier.name}",
                           "Confirm sailing/cutoff and raise carrier booking.", owner_role="operations",
                           shipment_id=shipment.id)

        self.db.commit()
        self.db.refresh(shipment)
        return shipment

    # ------------------------------------------------------------------
    def add_shipment_event(self, shipment_id: int, event_type: str, location: str | None = None,
                            notes: str | None = None, event_datetime: datetime.datetime | None = None,
                            container_id: int | None = None) -> ShipmentEvent:
        shipment = self.db.query(Shipment).get(shipment_id)
        if not shipment:
            raise ValueError("Shipment not found")

        event = ShipmentEvent(shipment_id=shipment_id, container_id=container_id, event_type=event_type,
                              event_datetime=event_datetime or datetime.datetime.utcnow(),
                              source="manual", location=location, notes=notes)
        self.db.add(event)

        new_stage = EVENT_STAGE_MAP.get(event_type)
        if new_stage:
            _audit(self.db, "shipment", shipment.id, "STAGE_CHANGED", actor="system",
                   from_value=shipment.stage, to_value=new_stage)
            shipment.stage = new_stage

        if event_type in MILESTONE_EMAIL_PURPOSE:
            result = self.ai.generate("customer_email", {
                "purpose": MILESTONE_EMAIL_PURPOSE[event_type], "reference": shipment.code,
                "carrier": shipment.carrier.name if shipment.carrier else None,
                "vessel": shipment.vessel_or_flight, "cutoff_date": shipment.cutoff_date,
                "document_cutoff_date": shipment.document_cutoff_date,
                "note": notes or event_type.replace("_", " ").title(),
            }, entity_type="shipment", entity_id=shipment.id)
            self.db.add(Communication(shipment_id=shipment.id, channel="email", direction="outbound",
                                       generated_by="ai", subject=result.decision["subject"],
                                       body=result.decision["body"], trigger_event=event_type))

        self.db.commit()
        self.db.refresh(event)
        return event
