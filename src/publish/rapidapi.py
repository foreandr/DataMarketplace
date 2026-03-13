from __future__ import annotations

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

try:
    from publish.spec_builder import build_spec_for_api
    from utils.config import load_json_config
except ModuleNotFoundError:  # allow running directly
    import sys

    ROOT_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT_DIR / "src"))
    from publish.spec_builder import build_spec_for_api
    from utils.config import load_json_config

load_dotenv()

class RapidAPIPublisher:
    def __init__(self, marketplace_name: str = "rapidapi"):
        cfg = load_json_config("marketplaces.json")
        mp = next((m for m in cfg.get("marketplaces", []) if m.get("name") == marketplace_name), None)
        if not mp:
            raise ValueError(f"Marketplace not found: {marketplace_name}")
        self.marketplace = mp
        self.base_url = (mp.get("base_url") or "").rstrip("/")
        self.create_endpoint = (mp.get("endpoints") or {}).get("create_api", "/apis")
        self.key = os.getenv((mp.get("auth") or {}).get("api_key_env", "RAPIDAPI_KEY"))
        self.host = (mp.get("auth") or {}).get("host")
        self.headers = {
            "Content-Type": "application/json",
        }
        if self.key:
            self.headers["x-rapidapi-key"] = self.key
        if self.host:
            self.headers["x-rapidapi-host"] = self.host

    def _build_payload(self, api_slug: str) -> dict:
        app_cfg = load_json_config("app.json")
        api = next((a for a in app_cfg.get("apis", []) if a.get("slug") == api_slug), None)
        if not api:
            raise ValueError(f"API not found in app.json: {api_slug}")

        spec_data = build_spec_for_api(api_slug)
        base_url = (app_cfg.get("server") or {}).get("base_url", "").rstrip("/")

        payload = {
            "name": api.get("name", api_slug),
            "description": api.get("description", ""),
            "baseUrl": base_url,
            "definition": spec_data,
            "visibility": api.get("visibility", "PUBLIC"),
        }
        extra = api.get("rapidapi_payload")
        if isinstance(extra, dict):
            payload.update(extra)
        return payload

    def publish_api(self, api_slug: str, dry_run: bool = False, out_dir: str | None = None) -> dict:
        payload = self._build_payload(api_slug)
        if dry_run:
            out = {
                "dry_run": True,
                "payload": payload,
                "using_key": self.key,
            }
            if out_dir:
                target = Path(out_dir)
                target.mkdir(parents=True, exist_ok=True)
                path = target / f"rapidapi_payload_{api_slug}.json"
                path.write_text(json.dumps(out, indent=2), encoding="utf-8")
            return out

        url = f"{self.base_url}{self.create_endpoint}"
        response = requests.post(url, json=payload, headers=self.headers, timeout=30)
        try:
            return response.json()
        except Exception:
            return {"status_code": response.status_code, "text": response.text}

if __name__ == "__main__":
    # =========================
    # CONFIG (edit these)
    # =========================
    API_SLUG = "craigslist_cars"
    DRY_RUN = True
    OUT_DIR = None
    # =========================

    publisher = RapidAPIPublisher()
    result = publisher.publish_api(API_SLUG, dry_run=DRY_RUN, out_dir=OUT_DIR)
    print(json.dumps(result, indent=2))
