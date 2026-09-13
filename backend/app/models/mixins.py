import datetime
import itertools

from sqlalchemy import Column, DateTime, Integer, String


class TimestampMixin:
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )


_counters = itertools.count(1)


def make_code(prefix: str, n: int) -> str:
    return f"{prefix}-{100000 + n}"
