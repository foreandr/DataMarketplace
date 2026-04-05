"""Schema for _upwork_jobs."""
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
        Field("posted_age", "TEXT", indexed=True),
        Field("job_type", "TEXT", indexed=True),
        Field("experience_level", "TEXT", indexed=True),
        Field("est_time", "TEXT"),
        Field("hourly_rate_min", "REAL", indexed=True),
        Field("hourly_rate_max", "REAL", indexed=True),
        Field("fixed_budget", "REAL", indexed=True),
        Field("description", "TEXT"),
        Field("skills", "TEXT", indexed=True),
        Field("is_featured", "INTEGER", indexed=True),
        Field("payment_verified", "INTEGER", indexed=True),
        Field("client_rating", "REAL", indexed=True),
        Field("client_spend", "TEXT"),
        Field("client_location", "TEXT", indexed=True),
        Field("proposals_range", "TEXT", indexed=True),
        Field("url", "TEXT", unique=True, indexed=True),
        Field("crawled_at", "TEXT", indexed=True, default_sql="CURRENT_TIMESTAMP"),
    ],
)
