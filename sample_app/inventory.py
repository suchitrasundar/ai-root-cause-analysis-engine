"""Stock tracking."""

STOCK: dict[str, int] = {}


class OutOfStock(Exception):
    pass


def load_stock(rows):
    """Load (sku, quantity) rows, e.g. from the nightly warehouse CSV."""
    for sku, qty in rows:
        STOCK[sku.lower()] = qty


def normalize_sku(sku: str) -> str:
    """Canonical SKU form used for all lookups."""
    return sku.strip().upper()


def reserve(sku: str, qty: int) -> None:
    key = normalize_sku(sku)
    if STOCK[key] < qty:
        raise OutOfStock(sku)
    STOCK[key] -= qty
