from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Coupon:
    code: str
    kind: str   # "percent" or "fixed"
    value: int  # percent points, or cents for "fixed"


@dataclass(frozen=True)
class Order:
    id: int
    total_cents: int
    created_at: datetime  # stored in UTC
