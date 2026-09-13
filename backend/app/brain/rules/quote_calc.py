"""Deterministic quote/pricing calculation engine — PRD2 s.14-16.

This is explicitly NOT AI: currency, rate and surcharge math must be reproducible and
auditable, per PRD1 s.30 / PRD2 s.3 ("Deterministic systems own... charge calculations").
The AI Gateway is only used upstream of this (extraction, HS candidates) and downstream
(narrative quote email) — never to compute the numbers themselves.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.reference import RateCard, Service


CUSTOMS_FLAT_FEE = 150.0
TRUCKING_FLAT_FEE = 300.0
INSURANCE_RATE = 0.005  # 0.5% of cargo value
RISK_CONTINGENCY_PCT = 0.02

MARGIN_BY_LABEL = {
    "Cheapest": 0.12,
    "Fastest": 0.18,
    "Recommended": 0.15,
}


@dataclass
class PricedOption:
    label: str
    carrier_id: int
    carrier_name: str
    rate_card_id: int
    transit_days: int
    reliability_score: float
    base_freight: float
    origin_charges: float
    destination_charges: float
    customs_charges: float
    trucking_charges: float
    documentation_charges: float
    surcharges: float
    insurance: float
    risk_contingency: float
    total_cost: float
    margin: float
    customer_price: float
    currency: str
    win_probability: float
    is_recommended: bool = False


def calculate_quote_options(db: Session, quote) -> list[PricedOption]:
    origin_id = quote.origin_port_location_id or quote.origin_location_id
    destination_id = quote.destination_port_location_id or quote.destination_location_id
    if not (origin_id and destination_id):
        return []

    equipment = quote.equipment or ("AIR_PALLET" if (quote.mode or "").startswith("air") else "40HC")
    quantity = max(quote.quantity or 1, 1)

    rate_cards = (
        db.query(RateCard)
        .filter(
            RateCard.origin_location_id == origin_id,
            RateCard.destination_location_id == destination_id,
        )
        .all()
    )
    # fall back to any equipment on the lane if exact equipment has no rate card
    exact = [rc for rc in rate_cards if rc.equipment == equipment]
    candidates = exact or rate_cards
    if not candidates:
        return []

    priced = []
    for rc in candidates:
        service = (
            db.query(Service)
            .filter(Service.carrier_id == rc.carrier_id,
                     Service.origin_location_id == rc.origin_location_id,
                     Service.destination_location_id == rc.destination_location_id)
            .first()
        )
        transit_days = service.transit_days if service else 30
        reliability = service.carrier.reliability_score if service else rc.carrier.reliability_score

        base_freight = rc.base_freight * quantity
        origin_charges = rc.origin_handling_fee * quantity
        destination_charges = rc.destination_handling_fee * quantity
        documentation_charges = rc.documentation_fee
        surcharges = base_freight * (rc.fuel_surcharge_pct / 100.0)
        customs_charges = CUSTOMS_FLAT_FEE if quote.customs_clearance_required else 0.0
        trucking_charges = TRUCKING_FLAT_FEE if quote.service_type == "door-to-door" else 0.0
        insurance = (quote.cargo_value or 0) * INSURANCE_RATE if quote.insurance_required else 0.0

        subtotal = (base_freight + origin_charges + destination_charges + documentation_charges
                    + surcharges + customs_charges + trucking_charges + insurance)
        risk_contingency = subtotal * RISK_CONTINGENCY_PCT
        total_cost = subtotal + risk_contingency

        priced.append(dict(
            carrier_id=rc.carrier_id, carrier_name=rc.carrier.name, rate_card_id=rc.id,
            transit_days=transit_days, reliability_score=reliability,
            base_freight=base_freight, origin_charges=origin_charges,
            destination_charges=destination_charges, customs_charges=customs_charges,
            trucking_charges=trucking_charges, documentation_charges=documentation_charges,
            surcharges=surcharges, insurance=insurance, risk_contingency=risk_contingency,
            total_cost=total_cost, currency=rc.currency,
        ))

    cheapest = min(priced, key=lambda p: p["total_cost"])
    fastest = min(priced, key=lambda p: p["transit_days"])

    # "recommended" = best balance of cost (normalised) and reliability, excluding pure-cheapest tradeoffs
    max_cost = max(p["total_cost"] for p in priced)
    min_cost = min(p["total_cost"] for p in priced)

    def score(p):
        cost_norm = 1 - ((p["total_cost"] - min_cost) / (max_cost - min_cost) if max_cost > min_cost else 0)
        return 0.5 * cost_norm + 0.5 * p["reliability_score"]

    recommended = max(priced, key=score)

    chosen = {"Cheapest": cheapest, "Fastest": fastest, "Recommended": recommended}
    # de-dup: if same rate card wins multiple labels, keep it once under the higher-priority label
    seen_rate_cards = set()
    options: list[PricedOption] = []
    for label in ["Recommended", "Fastest", "Cheapest"]:
        p = chosen[label]
        if p["rate_card_id"] in seen_rate_cards:
            continue
        seen_rate_cards.add(p["rate_card_id"])
        margin_pct = MARGIN_BY_LABEL[label]
        margin = p["total_cost"] * margin_pct
        customer_price = p["total_cost"] + margin
        win_probability = round(max(0.35, min(0.95, 0.9 - (customer_price - min_cost) / max(min_cost, 1) * 0.5)), 2)
        options.append(PricedOption(
            label=label, win_probability=win_probability, margin=margin,
            customer_price=customer_price, is_recommended=(label == "Recommended"),
            **p,
        ))

    # restore Cheapest/Fastest/Recommended left-to-right order for display
    order = {"Cheapest": 0, "Fastest": 1, "Recommended": 2}
    options.sort(key=lambda o: order[o.label])
    return options
