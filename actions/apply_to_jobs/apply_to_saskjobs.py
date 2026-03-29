"""
actions/apply_to_jobs/apply_to_goodwork.py

Open a GoodWork job listing in a browser and apply to it.
Internal application logic is handled by the caller.
"""
from __future__ import annotations
from typing import Any
from hyperSel import instance
from net_guard import ensure_page_loaded
import re
import email_sender
from files.application_data import generate_application
from keywords import SOFTWARE_KEYWORDS
from skip_emails import SKIP_EMAILS
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_TEST_DOMAINS = {"test.com", "example.com", "mailinator.com", "tempmail.com"}

def _is_software_title(title: str) -> bool:
    title_lower = (title or "").lower()
    if any(kw.lower() in title_lower for kw in SOFTWARE_KEYWORDS):
        return True
    signals = (
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
    return any(sig in title_lower for sig in signals)


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
    
    try:
        page_html = str(browser.return_current_soup()).lower()
        raw_emails = list(dict.fromkeys(EMAIL_RE.findall(page_html)))
        emails = [e for e in raw_emails if e.split("@")[-1] not in _TEST_DOMAINS]

        emails = [e for e in emails if e.lower() not in SKIP_EMAILS]
        if not emails:
            raise ValueError("no real email found on page (or all were skipped)")

        print(f"  [Saskjobs] emails found: {emails}")

        title = job.get("title", "the posted position")
        cover_letter_type = "swe" if _is_software_title(title) else "general"
        app = generate_application(
            job_title=title,
            job_board="Saskjobs",
            cover_letter_type=cover_letter_type,
        )

        for recipient in emails:
            email_sender.send_email(
                receiver=recipient,
                subject=app["subject"],
                body=app["body"],
                attachment_paths=app["attachments"],
                bcc_self=True,
            )
    finally:
        # input("--- CHECK")
        browser.close_browser()
