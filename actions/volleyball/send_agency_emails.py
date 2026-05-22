from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APPLY_TO_JOBS_PATH = ROOT / "actions" / "apply_to_jobs"
if str(APPLY_TO_JOBS_PATH) not in sys.path:
    sys.path.insert(0, str(APPLY_TO_JOBS_PATH))

import email_sender


TEST_MODE = False
TEST_RECEIVER = "foreandr@gmail.com"
AGENCIES_PATH = Path(__file__).with_name("agencies.txt")
CV_PATH = Path(__file__).with_name("Andre Foreman Volleyball CV.pdf")
LOG_PATH = Path(__file__).with_name("sent_agencies.txt")
EMAIL_SUBJECT = "Canadian Libero Available Immediately - Andre Foreman"
EMAIL_BODY = """Hello,

My name is Andre Foreman. I am a Canadian libero, available immediately, and I am looking for a professional opportunity.

I have been selected to Canada's Junior National Team, Canada's Full-Time Training Centre, and Canada's Men's B National Team.

Profile:
Position: Libero
Nationality: Canadian
Height: 183 cm
Block touch: 300 cm
Spike touch: 325 cm
Availability: Immediate

Video:
Full match: https://youtu.be/Tx4t8gYHm8c
Highlights: https://youtu.be/TgHYhQb2WlA

I have attached my volleyball CV. I would appreciate the chance to have my profile reviewed for any suitable professional opportunities in your network, especially in smaller European or international markets where my profile may be a good fit.

Best regards,
Andre Foreman
Email: foreandr@gmail.com
Phone / WhatsApp: +1 519-636-3173
"""


def iter_agencies() -> list[str]:
    return [
        line.strip()
        for line in AGENCIES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def append_send_log(original_agency: str, sent_to: str, test_mode: bool) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(
            f"{timestamp} | original_agency={original_agency} | "
            f"sent_to={sent_to} | test_mode={str(test_mode).lower()}\n"
        )


def iter_previously_sent_live_agencies() -> set[str]:
    if not LOG_PATH.exists():
        return set()

    sent_agencies: set[str] = set()
    for raw_line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or "test_mode=false" not in line:
            continue

        for part in line.split("|"):
            part = part.strip()
            if part.startswith("original_agency="):
                sent_agencies.add(part.split("=", 1)[1].strip())
                break

    return sent_agencies


def send_all(test_mode: bool = TEST_MODE) -> int:
    sent_count = 0
    agencies = iter_agencies()
    previously_sent_live_agencies = iter_previously_sent_live_agencies()

    if not CV_PATH.exists():
        raise FileNotFoundError(f"Missing CV attachment: {CV_PATH}")

    for agency in agencies:
        if not test_mode and agency in previously_sent_live_agencies:
            print("=" * 72)
            print(f"SKIPPING ALREADY-SENT LIVE AGENCY: {agency}")
            print("WAITING 5 SECONDS SO THIS IS CLEAR")
            print("=" * 72)
            time.sleep(5)
            continue

        receiver = TEST_RECEIVER if test_mode else agency
        print(f"sending to={receiver} original_agency={agency} test_mode={test_mode}")
        sent = email_sender.send_email(
            receiver=receiver,
            subject=EMAIL_SUBJECT,
            body=EMAIL_BODY,
            attachment_paths=[str(CV_PATH)],
            bcc_self=not test_mode,
        )
        if sent:
            sent_count += 1
            append_send_log(
                original_agency=agency,
                sent_to=receiver,
                test_mode=test_mode,
            )

    print(f"completed sent_count={sent_count} total={len(agencies)} test_mode={test_mode}")
    return sent_count


def main() -> int:
    send_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
