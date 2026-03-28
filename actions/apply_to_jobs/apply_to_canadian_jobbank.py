"""
actions/apply_to_jobs/apply_to_canadian_jobbank.py

Open a Canadian Job Bank job listing in a browser and apply to it.
Internal application logic is handled by the caller.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from typing import Any

from hyperSel import instance

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))
import email_sender
from keywords import SOFTWARE_KEYWORDS
from files.application_data import generate_application

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_TEST_DOMAINS = {"test.com", "example.com", "mailinator.com", "tempmail.com"}


def _is_software_title(title: str) -> bool:
    title_lower = (title or "").lower()
    if any(kw.lower() in title_lower for kw in SOFTWARE_KEYWORDS):
        return True
    strong_signals = (
        "software",
        "developer",
        "engineer",
        "full stack",
        "frontend",
        "backend",
        "devops",
        "data",
        "machine learning",
        "ml",
        "ai",
    )
    return any(sig in title_lower for sig in strong_signals)


def apply(job: dict[str, Any]) -> None:
    url = job.get("url")
    if not url:
        raise ValueError(f"canadian_jobbank job missing url: {job}")

    browser = instance.Browser(
        driver_choice='selenium',
        headless=False,
        zoom_level=100,
    )
    browser.init_browser()
    browser.go_to_site(url)

    page_text = browser.return_current_soup().get_text().lower()
    if "job posting no longer advertised" in page_text or "no longer available" in page_text:
        browser.close_browser()
        raise ValueError("job no longer available")


    try:
        SHOW_XPATH = '''//*[@id="applynowbutton"]'''
        browser.click_element(by_type="xpath", value=SHOW_XPATH)
        time.sleep(3)
    except Exception:
        raise ValueError("could not find apply button")
    
    try:
        ADDITIONAL_INFO_XPATH = '''/html/body/main/section/div[2]/div[1]/div[1]/div[8]/div/details'''
        browser.click_element(by_type="xpath", value=ADDITIONAL_INFO_XPATH )
        time.sleep(3)
    except Exception:
        raise ValueError("could not find apply button")
    
    
    
    page_html = str(browser.return_current_soup()).lower()
    raw_emails = list(dict.fromkeys(EMAIL_RE.findall(page_html)))
    emails = [e for e in raw_emails if e.split("@")[-1] not in _TEST_DOMAINS]

    if not emails:
        browser.close_browser()
        raise ValueError("no real email found on page")

    print(f"  [canadian_jobbank] emails found: {emails}")
    browser.close_browser()

    

    # ── send application email ─────────────────────────────────────────────────
    title = job.get("title", "the posted position")
    cover_letter_type = "swe" if _is_software_title(title) else "general"
    app = generate_application(
        job_title=title,
        job_board="Canadian Job Bank",
        cover_letter_type=cover_letter_type,
    )

    for recipient in emails:
        email_sender.send_email(
            receiver=recipient,
            subject=app["subject"],
            body=app["body"],
            attachment_paths=app["attachments"],
        )
    # input(f"[canadian_jobbank] Paused — press Enter to continue...")
