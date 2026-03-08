from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from utils.config import load_json_config, get_data_path
from crawlers.registry import load_crawler
from db.sqlite import (
    connect,
    init_db,
    insert_items,
    record_crawl_failure,
    record_crawl_success,
    ensure_source_table,
    get_last_crawled_at,
)


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


class _C:
    RESET = "\x1b[0m"
    DIM = "\x1b[2m"
    BOLD = "\x1b[1m"
    CYAN = "\x1b[36m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    RED = "\x1b[31m"
    MAGENTA = "\x1b[35m"


def _rule(label: str) -> str:
    return f"{_C.DIM}={'=' * 18}{_C.RESET} {_C.BOLD}{label}{_C.RESET} {_C.DIM}{'=' * 26}{_C.RESET}"


def _section(label: str) -> None:
    logging.info("")
    logging.info(_rule(label))
    logging.info("")


def _compute_delta(before: str | None, after: str | None) -> int | None:
    if not before or not after:
        return None
    try:
        b = datetime.fromisoformat(before)
        a = datetime.fromisoformat(after)
        return int((a - b).total_seconds())
    except Exception:
        return None


def _format_delta(seconds: int | None) -> str | None:
    if seconds is None:
        return None
    if seconds < 60:
        return f"{seconds} seconds"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec}s"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {minutes}m {sec}s"
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h {minutes}m {sec}s"


def main() -> None:
    load_dotenv()
    app_cfg = load_json_config("app.json")
    _setup_logging(app_cfg["app"]["log_level"])
    sources_cfg = load_json_config("sources.json")

    db_path = get_data_path(app_cfg["database"]["path"])
    conn = connect(db_path)
    init_db(conn)

    total = 0
    processed = 0
    failures = 0
    _section("Run Start")
    for source in sources_cfg.get("sources", []):
        if not source.get("enabled", False):
            logging.info("%sSkipping disabled source:%s %s", _C.DIM, _C.RESET, source.get("name"))
            continue

        crawler_cls = load_crawler(source["crawler"])
        crawler = crawler_cls(name=source["name"])

        prior = get_last_crawled_at(conn, source["name"])
        logging.info("%sRunning crawler:%s %s", _C.CYAN, _C.RESET, source["name"])
        logging.info("Last crawled at (before): %s", prior or "never")
        try:
            items = list(crawler.run()) if hasattr(crawler, "run") else []
        except NotImplementedError as exc:
            logging.error("%sCrawler not implemented:%s %s", _C.RED, _C.RESET, exc)
            record_crawl_failure(conn, source["name"], str(exc))
            failures += 1
            continue
        except Exception as exc:
            logging.error("%sCrawler failed:%s %s", _C.RED, _C.RESET, exc)
            record_crawl_failure(conn, source["name"], str(exc))
            failures += 1
            continue

        ensure_source_table(conn, source["name"])
        if items:
            count = insert_items(conn, items)
            total += count
            logging.info("%sInserted%s %s items from %s", _C.GREEN, _C.RESET, count, source["name"])
        else:
            record_crawl_success(conn, source["name"], "no_items")
            logging.info("%sNo items returned%s for %s", _C.YELLOW, _C.RESET, source["name"])
        after = get_last_crawled_at(conn, source["name"])
        delta = _compute_delta(prior, after)
        logging.info("Last crawled at (after): %s", after or "unknown")
        pretty_delta = _format_delta(delta)
        if pretty_delta is not None:
            logging.info("Delta since previous crawl: %s", pretty_delta)
        logging.info("%s", _C.DIM + " " + "=" * 72 + _C.RESET)
        processed += 1

    conn.close()
    _section("Run Summary")
    logging.info("%sSources processed:%s %s", _C.MAGENTA, _C.RESET, processed)
    logging.info("%sFailures:%s %s", _C.RED, _C.RESET, failures)
    logging.info("%sTotal items inserted:%s %s", _C.GREEN, _C.RESET, total)


if __name__ == "__main__":
    main()
