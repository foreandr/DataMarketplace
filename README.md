# Data Marketplace API

A lightweight data marketplace service that collects public data from multiple sources, stores it in structured SQLite databases, and exposes consistent query endpoints for downstream apps.

This system is designed to:
- Ingest data via modular crawlers
- Normalize output into predictable schemas
- Provide simple, documented query APIs
- Keep the infrastructure small and self-hostable

## What It Does

At a high level, the platform:
- Runs source-specific crawlers to collect data
- Transforms raw crawler output into structured rows
- Persists data in SQLite databases (one per collection)
- Exposes a uniform search API across collections
- Tracks health, logs, and operational telemetry

It is intended for building API products, internal dashboards, and data-driven tools that need reliable, queryable datasets without heavy infrastructure.

## How It Is Organized

Key locations in the repository:
- `src/crawlers/`: Source-specific crawlers
- `src/jsonify_logic/`: Transform logic to normalize crawler output
- `src/schemas/`: Table schemas for each collection
- `data/`: SQLite databases (one per collection)
- `config/`: Runtime and source configuration files
- `src/report/`: Operational reports and telemetry scripts
- `src/publish/`: Marketplace publishing scripts
- `src/tools/`: Add/remove crawler automation

## API Overview

Base URL:
- `/` renders this documentation

Core endpoints:
- `GET /health` returns service status
- `GET /schemas` lists available schemas
- `GET /v1/collections` lists available collections
- `POST /v1/collections/<name>/search` runs a query

Example search payload:
```json
{
  "select": ["*"],
  "filter": {"price": {"$gte": 5000}},
  "order_by": [{"field": "price", "direction": "asc"}],
  "limit": 100,
  "offset": 0
}
```

## Request Logging

All API requests are logged to `logs/api_requests.log` in JSONL format, including:
- IP and forwarding headers
- User agent and request metadata
- Full request headers
- Body snapshot (JSON when possible)

This log is intended for auditing, debugging, and usage analysis.

## Crawler Lifecycle

Adding a crawler:
- Generates crawler, schema, jsonify logic, and demo data stubs
- Inserts a new source entry into `config/sources.json`
- Creates a backing SQLite database in `data/`

Removing a crawler:
- Removes the source entry
- Deletes related code stubs and the database

The automation scripts live in `src/tools/`.

## Publishing

Marketplace publishing scripts live in `src/publish/` and each one targets a specific marketplace. They are intended to be run individually depending on where the dataset should be listed.

## Notes

This documentation is intentionally high-level so it stays accurate as sources evolve. The system is built to be extended by adding new sources without changing the API surface.
