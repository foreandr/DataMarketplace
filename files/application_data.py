from __future__ import annotations

import html

BASE = r"C:\Users\forea\Documents\DataMarketplace\files"

RESUME = f"{BASE}\\Andre Foreman Resume.pdf"
COVER_LETTERS = {
    "swe": f"{BASE}\\Andre Foreman Cover Letter.pdf",
    "general": f"{BASE}\\Andre_Foreman_Cover_Letter.pdf",
}
PORTFOLIO_URL = "https://foreandr.github.io/"
GITHUB_URL = "https://github.com/foreandr?tab=repositories"
PHONE_NUMBER = "5196363173"
EMAIL = "foreandr@gmail.com"


def _formatted_title(job_title: str) -> str:
    title = (job_title or "the posted position").strip()
    return title.title()


def _plain_body(job_title: str, job_url: str | None = None) -> str:
    title_text = _formatted_title(job_title)
    lines = [
        "Dear Hiring Management,",
        "",
        (
            f"My name is Andre Foreman, and I saw your {title_text} posting "
            "from the job board and wanted to reach out."
        ),
        (
            "I bring many years of experience across engineering, analytics, and a range "
            "of management and leadership roles, with a portfolio of shipped products "
            f"that reflects the quality and range of my work: here ({PORTFOLIO_URL})"
        ),
        (
            "I’d be grateful for the opportunity to contribute to your team and learn "
            "more about your business."
        ),
        "I've attached my resume below for your review.",
        "Please let me know if you feel I'd be a good fit for the role and would like to "
        "schedule a call or Zoom. Thank you for your time and consideration.",
    ]
    lines.extend(
        [
            "",
            "Andre Foreman",
            PHONE_NUMBER,
            EMAIL,
            PORTFOLIO_URL,
        ]
    )
    return "\n".join(lines)


def _html_body(job_title: str, job_url: str | None = None) -> str:
    title_text = html.escape(_formatted_title(job_title))
    del job_url
    title_markup = f"<strong><em>{title_text}</em></strong>"

    return f"""<html>
  <body>
    <p>Dear Hiring Management,</p>
    <p>My name is Andre Foreman, and I saw your {title_markup} posting from the job board and wanted to reach out.</p>
    <p>
      I bring many years of experience across engineering, analytics, and a range of management
      and leadership roles, with a portfolio of shipped products that reflects the quality and
      range of my work: <a href="{html.escape(PORTFOLIO_URL, quote=True)}">here</a>.
    </p>
    <p>
      I’d be grateful for the opportunity to contribute to your team and learn more about
      your business.
    </p>
    <p>I've attached my resume below for your review.</p>
    <p>Please let me know if you feel I'd be a good fit for the role and would like to schedule a call or Zoom. Thank you for your time and consideration.</p>
    <div style="margin-top:16px;font-family:Arial, sans-serif;line-height:1.5;">
      <div style="font-size:14px;font-weight:700;color:#111827;">Andre Foreman</div>
      <div style="margin-top:6px;font-size:12px;color:#4b5563;">
        <span style="font-weight:700;color:#374151;">Phone:</span> {html.escape(PHONE_NUMBER)}<br>
        <span style="font-weight:700;color:#374151;">Email:</span> <a href="mailto:{html.escape(EMAIL, quote=True)}" style="color:#1f2937;text-decoration:none;">{html.escape(EMAIL)}</a><br>
        <span style="font-weight:700;color:#374151;">Portfolio:</span> <a href="{html.escape(PORTFOLIO_URL, quote=True)}" style="color:#1f2937;text-decoration:none;">{html.escape(PORTFOLIO_URL)}</a>
      </div>
    </div>
  </body>
</html>"""


def generate_application(
    job_title: str,
    job_board: str,
    cover_letter_type: str = "swe",
    job_url: str | None = None,
) -> dict[str, object]:
    """
    Returns a dict with everything needed to send an application email.

    Args:
        job_title (str): e.g. "Data Analyst"
        job_board (str): e.g. "Indeed"
        cover_letter_type (str): retained for backward compatibility
        job_url (str | None): original job posting URL

    Returns:
        dict with keys: subject, body, body_html, attachments
    """
    del job_board, cover_letter_type
    formatted_title = _formatted_title(job_title)
    return {
        "subject": f"Application for {formatted_title} Role - Andre Foreman",
        "body": _plain_body(job_title, job_url=job_url),
        "body_html": _html_body(job_title, job_url=job_url),
        "attachments": [RESUME],
    }
