"""AI Gateway — the single interface every domain agent calls for anything AI-shaped
(PRD1 s.57-58, PRD2 s.40; the "Model gateway" line in the architecture diagram's
Control & Governance column).

    AIService.generate(task, context, schema) -> AIResult

Every result carries decision / confidence / facts / inferences / evidence /
recommended_action, and is logged to AIDecision for audit (PRD1 s.51-52, PRD2 s.60).

IMPORTANT — current build: this is a STUBBED gateway. It uses deterministic heuristics
(regex/keyword matching against seeded reference data) instead of a real LLM call, per the
"build the interface now, stub the model behind it" decision for this MVP. Swapping in a
real Claude call later means implementing `_call_model` only — every caller and the
AIDecision audit trail stay unchanged.
"""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AIDecision
from app.models.reference import Location, HSCode, TradeRule, Country, Product


@dataclass
class AIResult:
    decision: dict
    confidence: float
    facts: list[str] = field(default_factory=list)
    inferences: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    recommended_action: str | None = None
    model: str = "stub-heuristic-v1"
    prompt_version: str = "v1"


INCOTERMS = ["EXW", "FCA", "FOB", "FAS", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP"]

EQUIPMENT_PATTERNS = [
    (re.compile(r"(\d+)\s*x?\s*40\s*'?\s*hc", re.I), "40HC"),
    (re.compile(r"(\d+)\s*x?\s*40\s*'?\s*(gp|ft|feet|foot)?\b", re.I), "40GP"),
    (re.compile(r"(\d+)\s*x?\s*20\s*'?\s*(gp|ft|feet|foot)?\b", re.I), "20GP"),
    (re.compile(r"\blcl\b", re.I), "LCL"),
]

# lightweight commodity -> HS chapter keyword map, standing in for the real Product/HS
# ontology + embedding-based classifier described in PRD2 s.9-10
COMMODITY_HS_MAP = [
    (["ceramic", "tile", "tiles"], [("690721", 0.82), ("6907", 0.11), ("69", 0.07)]),
    (["auto part", "automotive", "car part", "vehicle part"], [("870829", 0.79), ("8708", 0.14), ("87", 0.07)]),
    (["sink", "stainless steel", "kitchen sink", "wash basin"], [("732410", 0.85), ("7324", 0.10), ("73", 0.05)]),
]

DANGEROUS_GOODS_KEYWORDS = ["battery", "lithium", "flammable", "chemical", "hazmat", "dangerous goods", "aerosol"]
TEMP_CONTROL_KEYWORDS = ["reefer", "refrigerated", "frozen", "chilled", "temperature control"]


class AIGateway:
    """Deterministic-stub implementation of the AIService.generate() contract."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    def generate(self, task: str, context: dict, schema: dict | None = None,
                 entity_type: str | None = None, entity_id: int | None = None) -> AIResult:
        handler = getattr(self, f"_task_{task}", None)
        if handler is None:
            raise ValueError(f"Unknown AI task: {task}")
        result = handler(context)
        if entity_type and entity_id:
            self._log_decision(task, entity_type, entity_id, context, result)
        return result

    def _log_decision(self, task, entity_type, entity_id, context, result: AIResult):
        rec = AIDecision(
            entity_type=entity_type,
            entity_id=entity_id,
            task=task,
            model=result.model,
            prompt_version=result.prompt_version,
            input_context=_json_safe(context),
            decision=_json_safe(result.decision),
            confidence=result.confidence,
            evidence=result.evidence,
            facts=result.facts,
            inferences=result.inferences,
            recommended_action=result.recommended_action,
            timestamp=datetime.datetime.utcnow(),
        )
        self.db.add(rec)
        self.db.flush()

    # ------------------------------------------------------------------
    # Task: shipment_extraction — free text -> structured QuoteRequirement fields
    # ------------------------------------------------------------------
    def _task_shipment_extraction(self, context: dict) -> AIResult:
        text = context["text"]
        low = text.lower()

        facts, inferences, evidence, uncertainties = [], [], [], []
        fields: dict[str, Any] = {}
        known, inferred, missing = [], [], []

        # --- locations: match against seeded Location names ---
        origin_loc = self._find_location_mention(text, after_word="from")
        dest_loc = self._find_location_mention(text, after_word="to")
        if origin_loc:
            fields["origin_location_id"] = origin_loc.id
            known.append("origin")
            facts.append(f"Origin location matched: '{origin_loc.name}'")
        else:
            missing.append("origin")
        if dest_loc:
            fields["destination_location_id"] = dest_loc.id
            known.append("destination")
            facts.append(f"Destination location matched: '{dest_loc.name}'")
        else:
            missing.append("destination")

        # --- equipment / mode ---
        equipment, quantity = None, None
        for pattern, eq in EQUIPMENT_PATTERNS:
            m = pattern.search(text)
            if m:
                equipment = eq
                if m.groups() and m.group(1) and m.group(1).isdigit():
                    quantity = int(m.group(1))
                break
        if equipment:
            fields["equipment"] = equipment
            fields["mode"] = "ocean_lcl" if equipment == "LCL" else "ocean_fcl"
            fields["quantity"] = quantity or 1
            known += ["equipment", "mode", "quantity"]
            facts.append(f"Equipment detected: {quantity or 1} x {equipment}")
        elif "pallet" in low:
            m = re.search(r"(\d+)\s*pallet", low)
            fields["mode"] = "ocean_lcl" if "ocean" in low or "sea" in low else "air"
            fields["package_type"] = "pallet"
            fields["quantity"] = int(m.group(1)) if m else None
            known += ["mode", "package_type"]
            inferences.append("Mode inferred as LCL/air from pallet-level cargo (no full container mentioned)")
        else:
            missing.append("equipment/mode")

        # --- incoterm / service type ---
        incoterm = next((i for i in INCOTERMS if re.search(rf"\b{i}\b", text, re.I)), None)
        if incoterm:
            fields["incoterm"] = incoterm
            known.append("incoterm")
            facts.append(f"Incoterm stated: {incoterm}")
        else:
            missing.append("incoterm")

        if "door-to-door" in low or "door to door" in low:
            fields["service_type"] = "door-to-door"
            fields["customs_clearance_required"] = True
            known.append("service_type")
        elif "port-to-port" in low or "port to port" in low:
            fields["service_type"] = "port-to-port"
            known.append("service_type")
        else:
            inferences.append("Service type not explicit — defaulted to door-to-door pending confirmation")
            fields["service_type"] = "door-to-door"
            inferred.append("service_type")

        if "customs" in low:
            fields["customs_clearance_required"] = True
            known.append("customs_clearance_required")

        # --- ready date (very loose match on month names / dd month) ---
        date_m = re.search(
            r"(ready\s*(?:around|on|by)?\s*)?(\d{1,2}(?:st|nd|rd|th)?\s+"
            r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*)",
            low,
        )
        if date_m:
            fields["ready_date"] = date_m.group(2)
            known.append("ready_date")
            facts.append(f"Cargo ready date mentioned: {date_m.group(2)}")
        else:
            missing.append("ready_date")

        # --- weight ---
        weight_m = re.search(r"([\d,.]+)\s*(kg|kgs|kilograms|tons?|tonnes?)", low)
        if weight_m:
            val = float(weight_m.group(1).replace(",", ""))
            unit = weight_m.group(2)
            if "ton" in unit:
                val *= 1000
            fields["weight_kg"] = val
            known.append("weight_kg")
        elif equipment:
            inferences.append("Weight not stated — will need shipper-confirmed weight before booking")
            missing.append("weight")
        else:
            missing.append("weight")

        # --- dangerous goods / temp control flags ---
        fields["dangerous_goods"] = any(k in low for k in DANGEROUS_GOODS_KEYWORDS)
        fields["temperature_control"] = any(k in low for k in TEMP_CONTROL_KEYWORDS)
        if fields["dangerous_goods"]:
            facts.append("Dangerous-goods keyword detected in request text")
            uncertainties.append("DG classification must be confirmed by compliance before booking")

        # --- cargo description: everything that looks like the commodity noun phrase ---
        commodity_m = re.search(r"of\s+([a-zA-Z ,\-]+?)(?:\s+from\b|\s+ready\b|\.|$)", text, re.I)
        cargo_description = commodity_m.group(1).strip() if commodity_m else None
        if cargo_description:
            fields["cargo_description"] = cargo_description
            known.append("cargo_description")
            facts.append(f"Cargo description extracted: '{cargo_description}'")
        else:
            missing.append("cargo_description")

        for addr_field in ("pickup_address", "delivery_address", "cargo_value"):
            missing.append(addr_field)

        confidence = round(min(0.97, 0.55 + 0.06 * len(known)), 2)

        decision = {
            "fields": fields,
            "known_fields": known,
            "inferred_fields": inferred,
            "missing_fields": sorted(set(missing)),
        }
        return AIResult(
            decision=decision,
            confidence=confidence,
            facts=facts,
            inferences=inferences,
            evidence=[f"Source text: \"{text.strip()[:200]}\""],
            uncertainties=uncertainties,
            recommended_action=(
                "Send missing-information request to customer before quoting"
                if missing else "Proceed to rate lookup and quote calculation"
            ),
        )

    def _find_location_mention(self, text: str, after_word: str) -> Location | None:
        m = re.search(rf"\b{after_word}\s+([A-Z][A-Za-zÀ-ɏ .]+?)(?=[,.]| to \b| from \b| ready\b| cargo\b|$)", text)
        candidate = m.group(1).strip() if m else None
        locations = self.db.query(Location).all()
        if candidate:
            for loc in locations:
                if loc.name.lower() in candidate.lower() or candidate.lower() in loc.name.lower():
                    return loc
        # fallback: scan whole text for any known location name
        for loc in locations:
            if re.search(rf"\b{re.escape(loc.name.split(' ')[0])}\b", text, re.I):
                # avoid matching origin token as destination and vice versa when both words share a hit
                if after_word == "from" and re.search(rf"from\b[^.]*\b{re.escape(loc.name.split(' ')[0])}", text, re.I):
                    return loc
                if after_word == "to" and re.search(rf"\bto\b[^.]*\b{re.escape(loc.name.split(' ')[0])}", text, re.I):
                    return loc
        return None

    # ------------------------------------------------------------------
    # Task: hs_classification
    # ------------------------------------------------------------------
    def _task_hs_classification(self, context: dict) -> AIResult:
        description = (context.get("cargo_description") or "").lower()
        candidates = []
        for keywords, hs_list in COMMODITY_HS_MAP:
            if any(k in description for k in keywords):
                candidates = hs_list
                break
        if not candidates:
            candidates = [("UNCLASSIFIED", 0.0)]

        enriched = []
        for code, conf in candidates:
            hs = self.db.query(HSCode).filter_by(code=code).first() if code != "UNCLASSIFIED" else None
            enriched.append({
                "code": code,
                "description": hs.description if hs else "No confident match — requires manual classification",
                "confidence": conf,
            })

        top = enriched[0]
        return AIResult(
            decision={"hs_candidates": enriched, "top_candidate": top},
            confidence=top["confidence"],
            facts=[f"Cargo description: '{context.get('cargo_description')}'"],
            inferences=[f"Classified against product-keyword mapping, top candidate {top['code']}"] if top["code"] != "UNCLASSIFIED" else [],
            evidence=["Product/HS keyword ontology (seeded subset)"],
            uncertainties=[] if top["confidence"] >= 0.75 else ["Low-confidence classification — route to customs/compliance for manual review"],
            recommended_action=(
                "Auto-accept top HS candidate" if top["confidence"] >= 0.75
                else "Route to customs analyst for manual HS classification"
            ),
        )

    # ------------------------------------------------------------------
    # Task: trade_rule_analysis — document + license checklist for a lane/HS/mode
    # ------------------------------------------------------------------
    def _task_trade_rule_analysis(self, context: dict) -> AIResult:
        country_id = context.get("destination_country_id")
        hs_code = context.get("hs_code")
        direction = context.get("direction", "import")

        q = self.db.query(TradeRule).filter(TradeRule.direction == direction)
        if country_id:
            q = q.filter(TradeRule.country_id == country_id)
        rules = q.all()

        applicable = []
        for r in rules:
            if r.hs_scope and hs_code and not hs_code.startswith(r.hs_scope):
                continue
            applicable.append({
                "requirement_type": r.requirement_type,
                "requirement": r.requirement,
                "severity": r.severity,
                "authority": r.authority,
                "source": r.source,
            })

        return AIResult(
            decision={"requirements": applicable},
            confidence=0.99,  # deterministic rule lookup, not a model guess
            facts=[f"{len(applicable)} trade rule(s) matched for direction={direction}, hs={hs_code}"],
            evidence=["TradeRule reference table (deterministic lookup, not an AI inference)"],
            recommended_action="Attach requirements to shipment document checklist",
            model="deterministic-rules-engine",
        )

    # ------------------------------------------------------------------
    # Task: customer_email — grounded narrative generation
    # ------------------------------------------------------------------
    def _task_customer_email(self, context: dict) -> AIResult:
        purpose = context.get("purpose", "quote_sent")
        body = _render_email(purpose, context)
        return AIResult(
            decision={"subject": _email_subject(purpose, context), "body": body},
            confidence=0.9,
            facts=["Generated from shipment/quote record fields only"],
            evidence=["Grounded in shipment/quote database record — no external facts introduced"],
            recommended_action="Human review optional below confidence threshold; send",
        )

    # ------------------------------------------------------------------
    # Task: root_cause — shipment risk / exception explanation
    # ------------------------------------------------------------------
    def _task_root_cause(self, context: dict) -> AIResult:
        primary = context.get("primary_cause")
        secondary = context.get("secondary_causes", [])
        exposure = context.get("exposure", 0)
        recommended = context.get("recommended_action", "Escalate to operations")
        return AIResult(
            decision={
                "primary_cause": primary,
                "secondary_causes": secondary,
                "estimated_exposure": exposure,
            },
            confidence=0.88,
            facts=[f"Primary blocker: {primary}"] + [f"Secondary: {s}" for s in secondary],
            evidence=["Shipment event timeline", "Free-time / LFD calculation"],
            recommended_action=recommended,
        )


def _json_safe(obj):
    import json
    try:
        json.dumps(obj)
        return obj
    except TypeError:
        return {"repr": str(obj)}


def _email_subject(purpose: str, context: dict) -> str:
    ref = context.get("reference", "")
    return {
        "quote_sent": f"Your freight quote {ref}",
        "missing_information": f"Information needed to quote {ref}",
        "booking_confirmed": f"Booking confirmed — {ref}",
        "shipment_update": f"Shipment update — {ref}",
    }.get(purpose, f"Update on {ref}")


def _render_email(purpose: str, context: dict) -> str:
    if purpose == "missing_information":
        missing = ", ".join(context.get("missing_fields", [])) or "a few details"
        return (
            f"Thank you for your enquiry ({context.get('reference')}). "
            f"To prepare an accurate quote we still need: {missing}. "
            f"Once we have these we can confirm rates and transit time."
        )
    if purpose == "quote_sent":
        opt = context.get("recommended_option", {})
        return (
            f"Please find our quote {context.get('reference')} for "
            f"{context.get('origin')} → {context.get('destination')} ({context.get('mode')}, {context.get('equipment')}). "
            f"Recommended option: {opt.get('label')} — {opt.get('currency')} {opt.get('customer_price')}, "
            f"transit approx. {opt.get('transit_days')} days. "
            f"The rate assumes {context.get('service_type', 'door-to-door')} service"
            + (", customs clearance included" if context.get("customs_clearance_required") else "")
            + f". Valid for 14 days from today."
        )
    if purpose == "booking_confirmed":
        vessel = context.get("vessel") or "to be confirmed"
        cutoff = context.get("cutoff_date") or "to be confirmed"
        doc_cutoff = context.get("document_cutoff_date") or "to be confirmed"
        return (
            f"Your shipment {context.get('reference')} has been booked with "
            f"{context.get('carrier')} — vessel/voyage {vessel}. "
            f"Cargo cutoff: {cutoff}, document cutoff: {doc_cutoff}."
        )
    return f"Update on shipment {context.get('reference')}: {context.get('note', '')}"
