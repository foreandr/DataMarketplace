from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()
HOST = os.environ["API_HOST"]
PORT = os.environ["API_PORT"]
BASE = f"http://{HOST}:{PORT}"


def _get(path: str) -> tuple[int, str]:
    resp = requests.get(BASE + path, timeout=30)
    return resp.status_code, resp.text


def _post(path: str, payload: dict) -> tuple[int, str]:
    resp = requests.post(BASE + path, json=payload, timeout=30)
    return resp.status_code, resp.text


def test_health() -> None:
    code, _ = _get("/health")
    assert code == 200


def test_schemas() -> None:
    code, _ = _get("/schemas")
    assert code == 200


def test_collections() -> None:
    code, _ = _get("/v1/collections")
    assert code == 200


def test_search_cars() -> None:
    payload = {
        "select": ["*"],
        "filter": {"price": {"$gte": 5000}},
        "order_by": [{"field": "price", "direction": "asc"}],
        "limit": 100,
        "offset": 0,
    }
    code, body = _post("/v1/collections/cars/search", payload)
    assert code == 200

    if os.environ.get("LOG_TEST_DATA", "").lower() in {"1", "true", "yes", "on"}:
        root = Path(__file__).resolve().parents[2]
        log_dir = root / "logs" / "test"
        log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        out_path = log_dir / f"test_data_{stamp}.json"
        try:
            parsed = json.loads(body)
            out_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
        except Exception:
            out_path.write_text(body, encoding="utf-8")
