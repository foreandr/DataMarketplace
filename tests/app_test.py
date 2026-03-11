from __future__ import annotations

import json
import os
import requests
from datetime import datetime
from pathlib import Path

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


def main() -> None:
    code, _ = _get("/health")
    print("GET /health:", code)

    code, _ = _get("/schemas")
    print("GET /schemas:", code)

    code, _ = _get("/v1/collections")
    print("GET /v1/collections:", code)

    payload = {
        "select": ["*"],
        "filter": {"price": {"$gte": 5000}},
        "order_by": [{"field": "price", "direction": "asc"}],
        "limit": 100,
        "offset": 0,
    }
    code, body = _post("/v1/collections/cars/search", payload)
    print("POST /v1/collections/cars/search:", code)

    if os.environ.get("LOG_TEST_DATA", "").lower() in {"1", "true", "yes", "on"}:
        root = Path(__file__).resolve().parents[1]
        log_dir = root / "logs" / "test"
        log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        out_path = log_dir / f"test_data_{stamp}.json"
        try:
            parsed = json.loads(body)
            out_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
        except Exception:
            out_path.write_text(body, encoding="utf-8")
        print("Wrote test data to:", out_path)


if __name__ == "__main__":
    main()
