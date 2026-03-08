from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from utils.config import load_json_config


# =========================
# CONFIG (edit these)
# =========================
SOURCE_NAME = "example_source"  # e.g., "imdb_movies"

# Optional: override module file name if it doesn't match SOURCE_NAME
MODULE_NAME = None  # e.g., "imdb"
# =========================


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def _derive_module_name(source_name: str) -> str:
    return source_name.replace("-", "_").lower()


def _crawler_file_path(module_name: str) -> Path:
    return SRC_DIR / "crawlers" / f"{module_name}.py"


def _load_sources(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_sources(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _remove_source_entry(sources_path: Path, source_name: str) -> bool:
    data = _load_sources(sources_path)
    sources = data.get("sources", [])
    new_sources = [s for s in sources if s.get("name") != source_name]
    if len(new_sources) == len(sources):
        return False
    data["sources"] = new_sources
    _write_sources(sources_path, data)
    return True


def _delete_crawler_stub(module_name: str) -> bool:
    path = _crawler_file_path(module_name)
    if not path.exists():
        return False
    path.unlink()
    return True


def main(source_name: str) -> None:
    load_dotenv()
    app_cfg = load_json_config("app.json")
    _setup_logging(app_cfg["app"]["log_level"])

    sources_path = ROOT_DIR / "config" / "sources.json"
    module_name = MODULE_NAME or _derive_module_name(source_name)

    removed = _remove_source_entry(sources_path, source_name)
    deleted = _delete_crawler_stub(module_name)

    logging.info("Removed source entry: %s", removed)
    logging.info("Deleted crawler file: %s", deleted)
    logging.info("Updated: %s", sources_path)


if __name__ == "__main__":
    main(SOURCE_NAME)
