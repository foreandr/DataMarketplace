"""Schema helpers for crawler-specific SQLite databases."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Field:
    name: str
    type: str  # SQLite type: TEXT, INTEGER, REAL, BLOB
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
            if f.primary:
                col += " PRIMARY KEY"
            if f.unique:
                col += " UNIQUE"
            if f.default_sql:
                col += f" DEFAULT {f.default_sql}"
            cols.append(col)
        cols_sql = ",\n            ".join(cols)
        return f"""
        CREATE TABLE IF NOT EXISTS {self.table} (
            {cols_sql}
        );
        """

    def create_indexes_sql(self) -> List[str]:
        stmts = []
        for f in self.fields:
            if f.indexed and not f.primary:
                idx_name = f"idx_{self.table}_{f.name}"
                stmts.append(
                    f"CREATE INDEX IF NOT EXISTS {idx_name} ON {self.table}({f.name});"
                )
        return stmts

    def field_names(self) -> List[str]:
        return [f.name for f in self.fields]
