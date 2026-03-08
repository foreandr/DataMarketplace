from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from utils.config import load_json_config, get_data_path
from utils.published import load_published_registry, record_published, published_key
from marketplaces.registry import load_publisher


SPEC_PATH = Path("config/api_spec.example.json")


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def main() -> None:
    load_dotenv()
    app_cfg = load_json_config("app.json")
    _setup_logging(app_cfg["app"]["log_level"])
    marketplaces_cfg = load_json_config("marketplaces.json")

    spec_path = SPEC_PATH
    if not spec_path.exists():
        raise FileNotFoundError(f"API spec not found: {spec_path}")
    api_spec = json.loads(spec_path.read_text(encoding="utf-8"))

    registry_path = get_data_path(app_cfg["published_registry"]["path"])
    published = load_published_registry(registry_path)

    for mp in marketplaces_cfg.get("marketplaces", []):
        if not mp.get("enabled", False):
            logging.info("Skipping disabled marketplace: %s", mp.get("name"))
            continue

        key = published_key(api_spec, mp["name"])
        if key in published:
            logging.info("Already published to %s: %s", mp["name"], key)
            continue

        publisher_cls = load_publisher(mp["integration"])
        publisher = publisher_cls(
            name=mp["name"],
            base_url=mp.get("base_url", ""),
            auth=mp.get("auth", {}),
        )

        logging.info("Publishing to: %s", mp["name"])
        try:
            result = publisher.publish(api_spec)
        except NotImplementedError as exc:
            logging.error("Publisher not implemented: %s", exc)
            continue

        logging.info("Result: %s | %s", result.success, result.message)
        if result.success:
            record_published(registry_path, api_spec, mp["name"], result.metadata)


if __name__ == "__main__":
    main()
