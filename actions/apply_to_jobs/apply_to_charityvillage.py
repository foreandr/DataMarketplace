"""
actions/apply_to_jobs/apply_to_charityvillage.py

Open a CharityVillage job listing in a browser and apply to it.
Internal application logic is handled by the caller.
"""
from __future__ import annotations

from typing import Any

from hyperSel import instance


def apply(job: dict[str, Any]) -> None:
    url = job.get("url")
    if not url:
        raise ValueError(f"charityvillage job missing url: {job}")

    browser = instance.Browser(
        driver_choice='selenium',
        headless=False,
        zoom_level=100,
    )
    browser.init_browser()
    browser.go_to_site(url)
    input(f"[charityvillage] Paused — press Enter to continue...")

    # ── internal application logic goes here ──────────────────────────────────

    browser.close_browser()
