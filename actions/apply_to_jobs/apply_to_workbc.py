"""
actions/apply_to_jobs/apply_to_workbc.py

WorkBC job application flow:
  1. Navigate to the job listing URL.
  2. Click the "How to Apply" button to reveal contact / email info.
  3. Wait for the panel to expand.
  4. Scrape all email addresses from the page HTML.
  5. Close the browser.
  6. Send an application email to each address found.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from typing import Any

from hyperSel import instance,log
from net_guard import ensure_page_loaded

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))

import email_sender
from keywords import SOFTWARE_KEYWORDS
from files.application_data import generate_application
from skip_emails import SKIP_EMAILS

EMAIL_RE    = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_TEST_DOMAINS = {"test.com", "example.com", "mailinator.com", "tempmail.com"}

# ── XPaths for the "How to Apply" reveal button ───────────────────────────────
# Try the ID-based selector first; fall back to the full absolute path.
_HOW_TO_APPLY_XPATHS = [
    '//*[@id="how-to-apply-button"]',
    '/html/body/div[1]/div[1]/div[2]/main/div/div[2]/div/div[2]/article/div/div[2]'
    '/app-root/div/app-job-detail/div/div/div/div[1]/div[4]/div/form/input',
]


def _is_software_title(title: str) -> bool:
    title_lower = (title or "").lower()
    if any(kw.lower() in title_lower for kw in SOFTWARE_KEYWORDS):
        return True
    strong_signals = (
        "software", "developer", "engineer", "full stack",
        "frontend", "backend", "devops", "data",
        "machine learning", "ml", "ai",
    )
    return any(sig in title_lower for sig in strong_signals)


def apply(job: dict[str, Any]) -> None:
    url = job.get("url")
    if not url:
        raise ValueError(f"workbc job missing url: {job}")

    browser = instance.Browser(
        driver_choice="selenium",
        headless=False,
        zoom_level=100,
    )
    browser.init_browser()
    browser.go_to_site(url)

    if not ensure_page_loaded(browser):
        browser.close_browser()
        raise ValueError("network hangup")

    page_text = browser.return_current_soup().get_text().lower()
    if "no longer available" in page_text or "job posting no longer" in page_text:
        browser.close_browser()
        raise ValueError("job no longer available")

    # ── Step 1: click the "How to Apply" button ───────────────────────────────
    log.checkpoint()
    from selenium.webdriver.common.by import By
    clicked = False
    for xpath in _HOW_TO_APPLY_XPATHS:
        try:
            el = browser.WEBDRIVER.find_element(By.XPATH, xpath)
            browser.scroll_to_item_in_view(element=el)
            time.sleep(0.5)
            try:
                el.click()
            except Exception:
                # Intercepted by overlay — force click via JS
                browser.WEBDRIVER.execute_script("arguments[0].click();", el)
            clicked = True
            print(f"  [workbc] clicked how-to-apply via: {xpath[:60]}...")
            break
        except Exception as e:
            print(f"  [workbc] xpath failed ({xpath[:60]}...): {e}")

    log.checkpoint()

    if not clicked:
        browser.close_browser()
        raise ValueError("could not find/click how-to-apply button")

    # ── Step 2: wait for the panel to expand ──────────────────────────────────
    time.sleep(3)

    # ── Step 3: scrape emails from the now-expanded page ─────────────────────
    page_html   = str(browser.return_current_soup()).lower()
    raw_emails  = list(dict.fromkeys(EMAIL_RE.findall(page_html)))
    emails      = [e for e in raw_emails if e.split("@")[-1] not in _TEST_DOMAINS]
    emails      = [e for e in emails if e.lower() not in SKIP_EMAILS]

    browser.close_browser()

    if not emails:
        raise ValueError("no real email found on page (or all were skipped)")

    print(f"  [workbc] emails found: {emails}")

    # ── Step 4: send application email ───────────────────────────────────────
    title = job.get("title", "the posted position")
    cover_letter_type = "swe" if _is_software_title(title) else "general"
    app = generate_application(
        job_title=title,
        job_board="WorkBC",
        cover_letter_type=cover_letter_type,
    )

    for recipient in emails:
        email_sender.send_email(
            receiver=recipient,
            subject=app["subject"],
            body=app["body"],
            attachment_paths=app["attachments"],
        )
