"""Revenue reporting."""
from datetime import timedelta, timezone

STORE_TZ = timezone(timedelta(hours=-8))  # the store operates on US Pacific time


def daily_revenue(orders) -> dict:
    """Total revenue per calendar day (store-local day)."""
    totals: dict = {}
    for order in orders:
        day = order.created_at.date()
        totals[day] = totals.get(day, 0) + order.total_cents
    return totals
