"""
actions/apply_to_jobs/email_sender.py

Send application emails via Gmail SMTP.
Supports HTML bodies and file attachments.
"""
from __future__ import annotations

import ssl
import smtplib
import time
from pathlib import Path
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import data

TEST_RECEIVER = "foreandr@gmail.com"


def send_email_with_account(
    email_sender: str,
    email_password: str,
    receiver: str,
    subject: str,
    body: str,
    body_html: str | None = None,
    attachment_paths: list[str] | None = None,
    bcc_self: bool = False,
) -> bool:
    content_to_check = (subject + " " + body).lower()
    keywords = ["car", "vehicle", "nurse", "medicine", "automobile"]

    if any(word in content_to_check for word in keywords):
        print("Keyword match found. Skipping send but returning success.")
        return True

    if attachment_paths and len(attachment_paths) > 1:
        attachment_paths = [attachment_paths[0]]

    print("==== EMAIL DEBUG INFO ====")
    print(f"Sender:   {email_sender}")
    print(f"Receiver: {receiver}")
    print(f"Subject:  {subject}")
    if attachment_paths:
        for p in attachment_paths:
            print(f"Attachment: {p}")
    else:
        print("No attachments.")
    print("==========================")

    msg = MIMEMultipart("mixed")
    msg["From"]    = email_sender
    msg["To"]      = receiver
    msg["Subject"] = subject
    if bcc_self:
        msg["Bcc"] = email_sender
    body_part = MIMEMultipart("alternative")
    body_part.attach(MIMEText(body, "plain", "utf-8"))
    if body_html:
        body_part.attach(MIMEText(body_html, "html", "utf-8"))
    msg.attach(body_part)

    for path in (attachment_paths or []):
        try:
            filename = Path(path).name
            with open(path, "rb") as fh:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(fh.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename=\"{filename}\"")
            msg.attach(part)
        except Exception as e:
            print(f"Failed to attach {path}: {e}")
            return False

    def _send_once() -> bool:
        context = ssl.create_default_context()
        recipients = [receiver]
        if bcc_self:
            recipients.append(email_sender)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
            smtp.login(email_sender, email_password)
            smtp.sendmail(email_sender, recipients, msg.as_string())
        return True

    try:
        if _send_once():
            print("Email sent successfully!")
            return True
    except smtplib.SMTPDataError as e:
        print(f"SMTPDataError: {e.smtp_code} - {e.smtp_error.decode()}")
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTPAuthenticationError: {e.smtp_code} - {e.smtp_error.decode()}")
    except smtplib.SMTPException as e:
        print(f"SMTPException: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    print("Google is rate limiting our emails, waiting 6 hours, then retrying...")
    time.sleep(6 * 60 * 60)
    try:
        if _send_once():
            print("Email sent successfully!")
            return True
    except smtplib.SMTPDataError as e:
        print(f"SMTPDataError: {e.smtp_code} - {e.smtp_error.decode()}")
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTPAuthenticationError: {e.smtp_code} - {e.smtp_error.decode()}")
    except smtplib.SMTPException as e:
        print(f"SMTPException: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    return False


def send_email(
    receiver: str,
    subject: str,
    body: str,
    body_html: str | None = None,
    attachment_paths: list[str] | None = None,
    account_index: int = 0,
    bcc_self: bool = False,
) -> bool:
    accounts = list(data.email_password_combinations.items())
    email_sender, email_password = accounts[account_index]
    return send_email_with_account(
        email_sender=email_sender,
        email_password=email_password,
        receiver=receiver,
        subject=subject,
        body=body,
        body_html=body_html,
        attachment_paths=attachment_paths,
        bcc_self=bcc_self,
    )
