"""Control-tower summary endpoint — a thin read model over Quote/Shipment/Exception,
standing in for the "Executive Dashboard" / "Shipment Control Tower" screens (PRD2 s.29,
PRD1 s.39-42)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.api.serializers import serialize_exception
from app.models.quote import Quote
from app.models.shipment import Shipment
from app.models.events import Exception_

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    quotes = db.query(Quote).all()
    shipments = db.query(Shipment).all()
    open_exceptions = db.query(Exception_).filter(Exception_.status == "OPEN").all()

    quoted_value = sum(
        (next((o.customer_price for o in q.options if o.is_recommended), 0) or 0)
        for q in quotes if q.status in ("QUOTED", "APPROVED")
    )
    approved_value = sum(
        (next((o.customer_price for o in q.options if o.id == q.approved_option_id), 0) or 0)
        for q in quotes if q.status == "APPROVED"
    )

    stage_counts: dict[str, int] = {}
    for s in shipments:
        stage_counts[s.stage] = stage_counts.get(s.stage, 0) + 1

    touchless = len([s for s in shipments if not any(e.status == "OPEN" for e in s.exceptions)])

    return {
        "quotes": {
            "total": len(quotes),
            "draft_or_missing_info": len([q for q in quotes if q.status in ("DRAFT", "MISSING_INFO")]),
            "quoted": len([q for q in quotes if q.status == "QUOTED"]),
            "approved": len([q for q in quotes if q.status == "APPROVED"]),
            "quoted_value_usd": round(quoted_value, 2),
            "approved_value_usd": round(approved_value, 2),
        },
        "shipments": {
            "total": len(shipments),
            "by_stage": stage_counts,
            "touchless_shipment_rate": round(touchless / len(shipments), 2) if shipments else None,
        },
        "exceptions": {
            "open": len(open_exceptions),
            "items": [serialize_exception(e) for e in open_exceptions],
        },
    }
