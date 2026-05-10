from __future__ import annotations

from files.application_data import generate_application


def test_generate_application_uses_richer_signature() -> None:
    application = generate_application(
        job_title="software developer",
        job_board="Indeed",
        job_url="https://example.com/job",
    )

    body = application["body"]
    body_html = application["body_html"]

    assert "Best regards," not in body
    assert "Andre Foreman" in body
    assert "5196363173" in body
    assert "foreandr@gmail.com" in body
    assert "https://foreandr.github.io/" in body

    assert "Best regards" not in body_html
    assert '<div style="font-size:14px;font-weight:700;color:#111827;">Andre Foreman</div>' in body_html
    assert "Phone:" in body_html
    assert "Email:" in body_html
    assert "Portfolio:" in body_html
    assert "5196363173" in body_html
    assert "foreandr@gmail.com" in body_html
    assert "https://foreandr.github.io/" in body_html


def test_generate_application_uses_current_outreach_copy() -> None:
    application = generate_application(
        job_title="senior data engineer",
        job_board="Indeed",
        job_url="https://example.com/job",
    )

    body = application["body"]
    body_html = application["body_html"]

    assert "from the job board and wanted to reach out" in body
    assert "from the job board and wanted to reach out" in body_html
    assert "many years of experience across engineering, analytics" in body
    assert "portfolio of shipped products" in body_html
    assert "learn more about your business" in body
    assert "learn more about" in body_html
    assert "your business" in body_html
    assert "schedule a call or Zoom" in body
    assert "schedule a call or Zoom" in body_html
    assert "Thank you for your time and consideration." in body
    assert "Thank you for your time and consideration." in body_html
