from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.config import load_json_config


ROOT_DIR = Path(__file__).resolve().parents[2]


def _render_template(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, str):
        rendered = value
        for key, val in context.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", str(val))
        return rendered
    if isinstance(value, list):
        return [_render_template(v, context) for v in value]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            new_key = _render_template(k, context) if isinstance(k, str) else k
            out[new_key] = _render_template(v, context)
        return out
    return value


def _load_base_spec() -> dict:
    path = ROOT_DIR / "config" / "api_spec.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing api_spec.json: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_app_config() -> dict:
    return load_json_config("app.json")


def _api_by_slug(app_cfg: dict, slug: str) -> dict:
    apis = app_cfg.get("apis", [])
    for api in apis:
        if api.get("slug") == slug:
            return api
    raise ValueError(f"API not found in app.json: {slug}")


def build_spec_for_api(slug: str) -> dict:
    app_cfg = _load_app_config()
    api = _api_by_slug(app_cfg, slug)
    base_url = (app_cfg.get("server") or {}).get("base_url", "").rstrip("/")
    base_spec = _load_base_spec()

    context = {
        "api_name": api.get("name", slug),
        "api_version": api.get("version", "1.0.0"),
        "api_description": api.get("description", ""),
        "base_url": base_url,
        "collection": api.get("collection", slug),
        "schema": api.get("schema", slug),
        "slug": slug,
    }
    return _render_template(base_spec, context)
