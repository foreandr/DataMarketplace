"""Schema for _craigslist_jobs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Field:
    name: str
    type: str
    primary: bool = False
    indexed: bool = False
    unique: bool = False
    default_sql: str | None = None


class Schema:
    def __init__(self, table: str, fields: List[Field]):
        self.table = table
        self.fields = fields

    def create_table_sql(self) -> str:
        cols = []
        for f in self.fields:
            col = f"{f.name} {f.type}"
            if f.primary: col += " PRIMARY KEY"
            if f.unique:  col += " UNIQUE"
            if f.default_sql: col += f" DEFAULT {f.default_sql}"
            cols.append(col)
        return f"CREATE TABLE IF NOT EXISTS {self.table} ({', '.join(cols)});"

    def create_indexes_sql(self) -> List[str]:
        return [
            f"CREATE INDEX IF NOT EXISTS idx_{self.table}_{f.name} ON {self.table}({f.name});"
            for f in self.fields if f.indexed and not f.primary
        ]

    def field_names(self) -> List[str]:
        return [f.name for f in self.fields]


SCHEMA = Schema(
    table="items",
    fields=[
        Field("id", "TEXT", primary=True),
        Field("title", "TEXT"),
        Field("location", "TEXT"),
        Field("pay", "REAL", indexed=True),
        Field("description", "TEXT"),
        Field("posted_date", "TEXT", indexed=True),
        Field("url", "TEXT", unique=True, indexed=True),
        Field("image_url", "TEXT"),
        Field("city", "TEXT", indexed=True),
        Field("state", "TEXT", indexed=True),
        Field("country", "TEXT", indexed=True),
        Field("crawled_at", "TEXT", indexed=True, default_sql="CURRENT_TIMESTAMP"),
    ],
)
