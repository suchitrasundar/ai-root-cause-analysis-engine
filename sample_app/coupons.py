"""Coupon rules.

Policy: at most ONE percentage coupon may apply per order (the best one wins).
Fixed-amount coupons may be combined with it.
"""
from .models import Coupon


def apply_coupons(subtotal_cents: int, coupons: list[Coupon]) -> int:
    total = subtotal_cents
    for coupon in coupons:
        if coupon.kind == "percent":
            total -= subtotal_cents * coupon.value // 100
        elif coupon.kind == "fixed":
            total -= coupon.value
    return max(total, 0)
