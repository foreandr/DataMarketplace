"""Configuration loading utilities."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT_DIR / "config"


def load_json_config(name: str) -> Dict[str, Any]:
    path = CONFIG_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def get_data_path(relative_path: str) -> Path:
    return ROOT_DIR / relative_path
