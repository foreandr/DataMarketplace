"""Schema for craigslist_cars cleaned data."""
from __future__ import annotations

from schemas.base import Field, Schema


SCHEMA = Schema(
    table="items",
    fields=[
        Field("id", "TEXT", primary=True),
        Field("title", "TEXT"),
        Field("year", "INTEGER", indexed=True),
        Field("region", "TEXT", indexed=True),
        Field("posted_at", "TEXT", indexed=True),
        Field("mileage", "INTEGER"),
        Field("price", "INTEGER", indexed=True),
        Field("url", "TEXT", unique=True, indexed=True),
        Field("image_url", "TEXT"),
    ],
)
