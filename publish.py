from __future__ import annotations

import importlib
from pathlib import Path


SPEC_PATH = Path("config/api_spec.example.json")
MARKETPLACES = [
    "rapidapi",
    "apify",
    "zyla_api_hub",
    "apilayer",
    "aws_data_exchange",
    "snowflake_marketplace",
    "datarade",
    "bright_data_marketplace",
    "oxylabs_marketplace",
]


def main() -> None:
    if not SPEC_PATH.exists():
        raise FileNotFoundError(f"API spec not found: {SPEC_PATH}")

    for name in MARKETPLACES:
        module = importlib.import_module(f"marketplaces.{name}")
        module.main(str(SPEC_PATH))


if __name__ == "__main__":
    main()
