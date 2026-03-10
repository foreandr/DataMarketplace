"""Schema stub for craigslist_realestate."""
from __future__ import annotations

from schemas.base import Field, Schema


SCHEMA = Schema(
    table="items",
    fields=[
        Field("id", "TEXT", primary=True),
        Field("title", "TEXT", indexed=True),
    ],
)
