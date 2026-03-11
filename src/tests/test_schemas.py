from __future__ import annotations


def test_schema_imports() -> None:
    from schemas.craigslist_cars import SCHEMA as cars_schema

    assert cars_schema.field_names(), "craigslist_cars schema has no fields"
