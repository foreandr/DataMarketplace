"""
actions/apply_to_jobs/apply_to_goodwork.py

Open a GoodWork job listing in a browser and apply to it.
Internal application logic is handled by the caller.
"""
from __future__ import annotations

from typing import Any

from hyperSel import instance
from net_guard import ensure_page_loaded


def apply(job: dict[str, Any]) -> None:
    url = job.get("url")
    if not url:
        raise ValueError(f"goodwork job missing url: {job}")

    browser = instance.Browser(
        driver_choice='selenium',
        headless=False,
        zoom_level=100,
    )
    browser.init_browser()
    browser.go_to_site(url)
    if not ensure_page_loaded(browser):
        browser.close_browser()
        raise ValueError("network hangup")
    input(f"[goodwork] Paused — press Enter to continue...")

    # ── internal application logic goes here ──────────────────────────────────

    browser.close_browser()
