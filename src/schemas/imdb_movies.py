"""Schema stub for imdb_movies."""
from __future__ import annotations

from schemas.base import Field, Schema


SCHEMA = Schema(
    table="items",
    fields=[
        Field("id", "TEXT", primary=True),
        Field("title", "TEXT", indexed=True),
        Field("crawled_at", "TEXT", indexed=True, default_sql="CURRENT_TIMESTAMP"),
    ],
)
