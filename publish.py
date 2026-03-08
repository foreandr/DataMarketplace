from __future__ import annotations

from pathlib import Path

from main import publish_task


SPEC_PATH = Path("config/api_spec.example.json")

if __name__ == "__main__":
    publish_task(str(SPEC_PATH))
