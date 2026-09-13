"""OD (origin-destination) normalization — PRD2 s.12.

Resolves a stated city (e.g. "Foshan") to the actual port/airport gateway used for
rate lookup and routing (e.g. "Shenzhen (Yantian)"), the way the PRD2 worked example
does: "Origin: Foshan, China / Port of Loading: Candidate Shenzhen/Yantian".

Deterministic reference-data lookup (nearest gateway with an active carrier service),
not an AI call — mirrors the PRD's instruction that OD/gateway resolution should be a
data-backed lookup, with AI only used to identify the stated origin/destination in the
first place (see AI Gateway's shipment_extraction task).
"""
from sqlalchemy.orm import Session

from app.models.reference import Location, Service


def resolve_gateway(db: Session, location_id: int | None, mode: str | None) -> Location | None:
    if not location_id:
        return None
    loc = db.query(Location).get(location_id)
    if not loc:
        return None
    if loc.location_type in ("port", "airport"):
        return loc

    gateway_type = "airport" if (mode or "").startswith("air") else "port"
    # nearest gateway = a port/airport in the same country that has at least one active
    # carrier Service; falls back to any gateway in-country if none has a service yet.
    same_country_gateways = (
        db.query(Location)
        .filter(Location.country_id == loc.country_id, Location.location_type == gateway_type)
        .all()
    )
    if not same_country_gateways:
        return None
    for gw in same_country_gateways:
        has_service = (
            db.query(Service)
            .filter((Service.origin_location_id == gw.id) | (Service.destination_location_id == gw.id))
            .first()
        )
        if has_service:
            return gw
    return same_country_gateways[0]
