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
from files.application_data import generate_application
from skip_emails import SKIP_EMAILS
from net_guard import ensure_page_loaded

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_TEST_DOMAINS = {"test.com", "example.com", "mailinator.com", "tempmail.com"}


def apply(job: dict[str, Any]) -> None:
    try:
        url = job.get("url")
        if not url:
            raise ValueError(f"canadian_jobbank job missing url: {job}")

        browser = instance.Browser(
            driver_choice='selenium',
            headless=True,
            zoom_level=100,
        )
        browser.init_browser()
        browser.go_to_site(url)
        if not ensure_page_loaded(browser):
            browser.close_browser()
            raise ValueError("network hangup")

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

        emails = [e for e in emails if e.lower() not in SKIP_EMAILS]
        if not emails:
            browser.close_browser()
            raise ValueError("no real email found on page (or all were skipped)")

        print(f"  [canadian_jobbank] emails found: {emails}")
        browser.close_browser()

        # ── send application email ─────────────────────────────────────────────────
        title = job.get("title", "the posted position")
        app = generate_application(
            job_title=title,
            job_board="Canadian Job Bank",
            job_url=url,
        )
        browser.close_browser()

        for recipient in emails:
            email_sender.send_email(
                receiver=recipient,
                subject=app["subject"],
                body=app["body"],
                body_html=app["body_html"],
                attachment_paths=app["attachments"],
            )
        browser.close_browser()
        # input(f"[canadian_jobbank] Paused — press Enter to continue...")
    except Exception as e:
        browser.close_browser()
        print("GOD ONLY KNOWS")
        
