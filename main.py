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
from utils.published import (
    load_published_registry,
    record_published,
    published_key,
)
from crawlers.registry import load_crawler
from db.sqlite import connect, init_db, insert_items
from marketplaces.registry import load_publisher


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def init_db_task() -> None:
    load_dotenv()
    app_cfg = load_json_config("app.json")
    _setup_logging(app_cfg["app"]["log_level"])

    db_path = get_data_path(app_cfg["database"]["path"])
    conn = connect(db_path)
    init_db(conn)
    conn.close()
    logging.info("Initialized database at %s", db_path)


def run_crawlers_task() -> None:
    load_dotenv()
    app_cfg = load_json_config("app.json")
    _setup_logging(app_cfg["app"]["log_level"])

    sources_cfg = load_json_config("sources.json")

    db_path = get_data_path(app_cfg["database"]["path"])
    conn = connect(db_path)
    init_db(conn)

    total = 0
    for source in sources_cfg.get("sources", []):
        if not source.get("enabled", False):
            logging.info("Skipping disabled source: %s", source.get("name"))
            continue

        crawler_cls = load_crawler(source["crawler"])
        crawler = crawler_cls(
            name=source["name"],
            item_type=source["item_type"],
            seed_urls=source.get("seed_urls", []),
        )

        logging.info("Running crawler: %s", source["name"])
        try:
            items = list(crawler.run())
        except NotImplementedError as exc:
            logging.error("Crawler not implemented: %s", exc)
            continue

        count = insert_items(conn, items)
        total += count
        logging.info("Inserted %s items from %s", count, source["name"])

    conn.close()
    logging.info("Total items inserted: %s", total)


def publish_task(api_spec_path: str) -> None:
    load_dotenv()
    app_cfg = load_json_config("app.json")
    _setup_logging(app_cfg["app"]["log_level"])

    marketplaces_cfg = load_json_config("marketplaces.json")

    spec_path = Path(api_spec_path)
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
