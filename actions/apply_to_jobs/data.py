"""
actions/apply_to_jobs/data.py

Email account credentials — loaded from .env so passwords stay out of source.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

email_password_combinations: dict[str, str] = {
    "foreandr@gmail.com":        os.getenv("FOREANDR_PASSWORD", ""),
    "fyneandr@gmail.com":        os.getenv("FYNEANDR_PASSWORD", ""),
    "andrfore@gmail.com":        os.getenv("ANDRFORE_PASSWORD", ""),
    "throughvenslens@gmail.com": os.getenv("THROUGHVENSLENS_PASSWORD", ""),  # Venessa Mitchell
}
