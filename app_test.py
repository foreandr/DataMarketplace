from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()
HOST = os.environ["API_HOST"]
PORT = os.environ["API_PORT"]
BASE = f"http://{HOST}:{PORT}"


def _get(path: str) -> tuple[int, str]:
    req = urllib.request.Request(BASE + path, method="GET")
    with urllib.request.urlopen(req) as resp:
        return resp.status, resp.read().decode("utf-8")


def _post(path: str, payload: dict) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status, resp.read().decode("utf-8")


def main() -> None:
    code, body = _get("/health")
    print("GET /health:", code, body)

    code, body = _get("/schemas")
    print("GET /schemas:", code, body)

    payload = {
        "db_path": "data/craigslist_cars.sqlite",
        "schema": "craigslist_cars",
        "select": ["*"],
        "where": [{"field": "price", "op": ">=", "value": 5000}],
        "order_by": [{"field": "price", "direction": "asc"}],
    }
    code, body = _post("/query", payload)
    print("POST /query:", code, body)

    if os.environ.get("LOG_TEST_DATA", "").lower() in {"1", "true", "yes", "on"}:
        log_dir = Path("logs") / "test"
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
