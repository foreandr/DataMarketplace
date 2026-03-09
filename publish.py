from __future__ import annotations

import importlib
from pathlib import Path


SPEC_PATH = Path("config/api_spec.example.json")
MARKETPLACES = ["apilayer", "rapidapi", "zyla_api_hub"]


def main() -> None:
    if not SPEC_PATH.exists():
        raise FileNotFoundError(f"API spec not found: {SPEC_PATH}")

    for name in MARKETPLACES:
        module = importlib.import_module(f"marketplaces.{name}")
        module.main(str(SPEC_PATH))


if __name__ == "__main__":
    main()
