"""Free-time / last-free-day / demurrage exposure calculator — PRD1 s.16-21.

Deterministic by design ("do not hard-code free time = X days; do not let AI compute
financial exposure"). Kept here so the same rules engine module backs both the
enquiry-to-delivery workflow (container free-time shown on the shipment timeline) and a
future invoice-reconciliation build.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass


@dataclass
class DemurrageStatus:
    last_free_day: datetime.datetime
    days_remaining: int
    risk_level: str  # LOW|MEDIUM|HIGH|CRITICAL
    exposure_if_today: float


def calculate_last_free_day(discharge_datetime: datetime.datetime, free_days: int) -> datetime.datetime:
    return discharge_datetime + datetime.timedelta(days=free_days)


def calculate_demurrage_status(discharge_datetime: datetime.datetime, free_days: int,
                                demurrage_tiers: list[dict], as_of: datetime.datetime | None = None) -> DemurrageStatus:
    as_of = as_of or datetime.datetime.utcnow()
    lfd = calculate_last_free_day(discharge_datetime, free_days)
    days_remaining = (lfd - as_of).days

    if days_remaining > 4:
        risk = "LOW"
    elif days_remaining > 2:
        risk = "MEDIUM"
    elif days_remaining >= 0:
        risk = "HIGH"
    else:
        risk = "CRITICAL"

    overdue_days = max(0, (as_of - lfd).days)
    exposure = 0.0
    for tier in demurrage_tiers:
        tier_days = max(0, min(overdue_days, tier["to_day"]) - tier["from_day"] + 1) if overdue_days >= tier["from_day"] else 0
        exposure += tier_days * tier["rate"]

    return DemurrageStatus(last_free_day=lfd, days_remaining=days_remaining, risk_level=risk,
                            exposure_if_today=exposure)
