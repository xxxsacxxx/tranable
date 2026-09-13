from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.api.serializers import serialize_customer, serialize_carrier, serialize_location
from app.models.customer import Customer
from app.models.reference import Carrier, Location
from app.models.events import EVENT_TYPES

router = APIRouter(tags=["reference"])


@router.get("/customers")
def list_customers(db: Session = Depends(get_db)):
    return [serialize_customer(c) for c in db.query(Customer).order_by(Customer.name).all()]


@router.get("/carriers")
def list_carriers(db: Session = Depends(get_db)):
    return [serialize_carrier(c) for c in db.query(Carrier).order_by(Carrier.name).all()]


@router.get("/locations")
def list_locations(db: Session = Depends(get_db)):
    return [serialize_location(l) for l in db.query(Location).order_by(Location.name).all()]


@router.get("/event-types")
def list_event_types():
    return EVENT_TYPES
