from __future__ import annotations

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

SPEC_PATH = ROOT_DIR / "config" / "api_spec.example.json"


def main() -> None:
    if not SPEC_PATH.exists():
        raise FileNotFoundError(f"API spec not found: {SPEC_PATH}")

    from marketplaces.bright_data_marketplace import main as publish_main

    publish_main(str(SPEC_PATH))


if __name__ == "__main__":
    main()
