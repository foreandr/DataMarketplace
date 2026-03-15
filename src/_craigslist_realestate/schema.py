"""Schema stub for _craigslist_realestate."""
from __future__ import annotations

from lib import Field, Schema


SCHEMA = Schema(
    table="items",
    fields=[
        Field("id", "TEXT", primary=True),
        Field("title", "TEXT", indexed=True),
        Field("crawled_at", "TEXT", indexed=True, default_sql="CURRENT_TIMESTAMP"),
    ],
)
