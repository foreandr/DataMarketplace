from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))

import email_sender
from files.application_data import generate_application


def main() -> int:
    receiver = sys.argv[1] if len(sys.argv) > 1 else "foreandr@gmail.com"
    job_title = sys.argv[2] if len(sys.argv) > 2 else "Senior Data Engineer"
    job_board = sys.argv[3] if len(sys.argv) > 3 else "Indeed"

    application = generate_application(
        job_title=job_title,
        job_board=job_board,
    )

    sent = email_sender.send_email(
        receiver=receiver,
        subject=application["subject"],
        body=application["body"],
        body_html=application["body_html"],
        attachment_paths=application["attachments"],
    )

    print(f"send_sample_application sent={sent} to={receiver} title={job_title!r}")
    return 0 if sent else 1


if __name__ == "__main__":
    raise SystemExit(main())
