from pydantic import BaseModel


class CreateQuoteRequest(BaseModel):
    raw_text: str
    customer_id: int | None = None
    source: str = "email"


class ApproveQuoteRequest(BaseModel):
    option_id: int


class AddShipmentEventRequest(BaseModel):
    event_type: str
    location: str | None = None
    notes: str | None = None
