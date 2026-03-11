from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from utils.config import load_json_config
from crawlers.registry import load_crawler


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


def main() -> None:
    load_dotenv()
    app_cfg = load_json_config("app.json")
    _setup_logging(app_cfg["app"]["log_level"])
    sources_cfg = load_json_config("sources.json")

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

        logging.info("%sRunning crawler:%s %s", _C.CYAN, _C.RESET, source["name"])
        start_ts = datetime.now().isoformat(timespec="seconds")
        logging.info("Start time: %s", start_ts)
        try:
            items = list(crawler.run()) if hasattr(crawler, "run") else []
        except NotImplementedError as exc:
            logging.error("%sCrawler not implemented:%s %s", _C.RED, _C.RESET, exc)
            failures += 1
            continue
        except Exception as exc:
            logging.error("%sCrawler failed:%s %s", _C.RED, _C.RESET, exc)
            failures += 1
            continue

        if items:
            total += len(items)
            logging.info("%sCrawler returned%s %s items from %s", _C.GREEN, _C.RESET, len(items), source["name"])
        else:
            logging.info("%sNo items returned%s for %s", _C.YELLOW, _C.RESET, source["name"])
        end_ts = datetime.now().isoformat(timespec="seconds")
        logging.info("End time: %s", end_ts)
        logging.info("%s", _C.DIM + " " + "=" * 72 + _C.RESET)
        processed += 1

    _section("Run Summary")
    logging.info("%sSources processed:%s %s", _C.MAGENTA, _C.RESET, processed)
    logging.info("%sFailures:%s %s", _C.RED, _C.RESET, failures)
    logging.info("%sTotal items inserted:%s %s", _C.GREEN, _C.RESET, total)


if __name__ == "__main__":
    main()
