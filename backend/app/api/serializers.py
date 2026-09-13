"""Plain-dict serializers for API responses (no separate Pydantic response models yet —
kept intentionally simple for this first build; swap for pydantic-from-orm schemas once the
shape stabilises)."""


def _dt(v):
    return v.isoformat() if v else None


def serialize_location(loc):
    if not loc:
        return None
    return {"id": loc.id, "name": loc.name, "type": loc.location_type,
            "country": loc.country.name if loc.country else None, "unlocode": loc.unlocode}


def serialize_carrier(c):
    if not c:
        return None
    return {"id": c.id, "name": c.name, "mode": c.mode, "reliability_score": c.reliability_score}


def serialize_customer(c):
    if not c:
        return None
    return {"id": c.id, "name": c.name, "account_owner": c.account_owner,
            "default_incoterm": c.default_incoterm}


def serialize_option(o):
    return {
        "id": o.id, "label": o.label, "is_recommended": o.is_recommended,
        "carrier": serialize_carrier(o.carrier), "transit_days": o.transit_days,
        "reliability_score": o.reliability_score,
        "breakdown": {
            "base_freight": round(o.base_freight, 2), "origin_charges": round(o.origin_charges, 2),
            "destination_charges": round(o.destination_charges, 2), "customs_charges": round(o.customs_charges, 2),
            "trucking_charges": round(o.trucking_charges, 2), "documentation_charges": round(o.documentation_charges, 2),
            "surcharges": round(o.surcharges, 2), "insurance": round(o.insurance, 2),
            "risk_contingency": round(o.risk_contingency, 2), "total_cost": round(o.total_cost, 2),
            "margin": round(o.margin, 2),
        },
        "customer_price": round(o.customer_price, 2), "currency": o.currency,
        "win_probability": o.win_probability,
    }


def serialize_communication(c):
    return {"id": c.id, "channel": c.channel, "direction": c.direction, "generated_by": c.generated_by,
            "subject": c.subject, "body": c.body, "trigger_event": c.trigger_event, "created_at": _dt(c.created_at)}


def serialize_exception(e):
    return {"id": e.id, "entity_type": e.entity_type, "exception_type": e.exception_type,
            "severity": e.severity, "status": e.status, "amount_at_risk": e.amount_at_risk,
            "reason": e.reason, "recommended_action": e.recommended_action, "created_at": _dt(e.created_at)}


def serialize_task(t):
    return {"id": t.id, "title": t.title, "description": t.description, "status": t.status,
            "owner_role": t.owner_role, "created_at": _dt(t.created_at)}


def serialize_document(d):
    return {"id": d.id, "document_type": d.document_type, "requirement_level": d.requirement_level,
            "status": d.status, "validation_notes": d.validation_notes}


def serialize_ai_decision(d):
    return {
        "id": d.id, "task": d.task, "model": d.model, "prompt_version": d.prompt_version,
        "confidence": d.confidence, "facts": d.facts, "inferences": d.inferences,
        "evidence": d.evidence, "recommended_action": d.recommended_action,
        "decision": d.decision, "human_override": d.human_override, "timestamp": _dt(d.timestamp),
    }


def serialize_event(e):
    return {"id": e.id, "event_type": e.event_type, "event_datetime": _dt(e.event_datetime),
            "source": e.source, "location": e.location, "notes": e.notes, "container_id": e.container_id}


def serialize_quote(q, detailed=False):
    base = {
        "id": q.id, "code": q.code, "status": q.status, "customer": serialize_customer(q.customer),
        "raw_request_text": q.raw_request_text, "created_at": _dt(q.created_at),
        "origin": serialize_location(q.origin), "destination": serialize_location(q.destination),
        "origin_port": serialize_location(q.origin_port), "destination_port": serialize_location(q.destination_port),
        "mode": q.mode, "equipment": q.equipment, "quantity": q.quantity, "service_type": q.service_type,
        "incoterm": q.incoterm, "cargo_description": q.cargo_description, "hs_code_candidate": q.hs_code_candidate,
        "ready_date": q.ready_date, "customs_clearance_required": q.customs_clearance_required,
        "dangerous_goods": q.dangerous_goods,
        "extraction_confidence": q.extraction_confidence,
        "known_fields": q.known_fields, "inferred_fields": q.inferred_fields, "missing_fields": q.missing_fields,
        "approved_option_id": q.approved_option_id,
    }
    if detailed:
        base["hs_candidates"] = q.hs_candidates_json
        base["options"] = [serialize_option(o) for o in sorted(q.options, key=lambda o: o.id)]
    return base


def serialize_shipment(s, detailed=False):
    base = {
        "id": s.id, "code": s.code, "stage": s.stage, "customer": serialize_customer(s.customer),
        "carrier": serialize_carrier(s.carrier), "origin": serialize_location(s.origin),
        "destination": serialize_location(s.destination), "mode": s.mode, "equipment": s.equipment,
        "incoterm": s.incoterm, "risk_level": s.risk_level, "is_at_risk": s.is_at_risk,
        "booking_reference": s.booking_reference, "vessel_or_flight": s.vessel_or_flight,
        "cutoff_date": s.cutoff_date, "document_cutoff_date": s.document_cutoff_date,
        "created_at": _dt(s.created_at),
        "order_code": s.order.code if s.order else None,
        "quote_code": s.order.quote.code if s.order and s.order.quote else None,
    }
    if detailed:
        base["events"] = [serialize_event(e) for e in s.events]
        base["documents"] = [serialize_document(d) for d in s.documents]
        base["exceptions"] = [serialize_exception(e) for e in s.exceptions]
        base["communications"] = [serialize_communication(c) for c in s.communications]
    return base
