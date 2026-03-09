"""Datarade upload placeholder."""
from __future__ import annotations

from pathlib import Path


def main(spec_path: str) -> None:
    path = Path(spec_path)
    print(f"[Datarade] Upload placeholder for: {path}")


if __name__ == "__main__":
    main("config/api_spec.example.json")
