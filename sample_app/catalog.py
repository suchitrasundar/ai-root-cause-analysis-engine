"""Catalog browsing."""


def paginate(items: list, page: int, per_page: int = 10) -> list:
    """Return one page of items. Pages are numbered from 1."""
    start = (page - 1) * per_page
    end = start + per_page - 1
    return items[start:end]
