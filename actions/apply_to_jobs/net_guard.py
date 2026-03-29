"""
actions/apply_to_jobs/net_guard.py

Detects page-load hangups and skips safely.
"""
from __future__ import annotations

import time


def ensure_page_loaded(browser, timeout_sec: float = 20.0) -> bool:
    """Return True if page load completes within timeout; otherwise print and return False."""
    driver = getattr(browser, "WEBDRIVER", None)
    if driver is None:
        return True

    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            state = driver.execute_script("return document.readyState")
            if state == "complete":
                return True
        except Exception:
            pass
        time.sleep(0.5)

    print("\033[96mNETWORK HANGUP skipping to next\033[0m")
    return False
