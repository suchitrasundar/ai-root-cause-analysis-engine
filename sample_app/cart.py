"""Checkout flow."""
from . import inventory
from .coupons import apply_coupons


def checkout(items: list[tuple[str, int, int]], coupons: list) -> int:
    """items: (sku, quantity, unit_price_cents). Returns the amount to charge in cents."""
    subtotal = 0
    for sku, qty, unit_price in items:
        inventory.reserve(sku, qty)
        subtotal += qty * unit_price
    return apply_coupons(subtotal, coupons)
