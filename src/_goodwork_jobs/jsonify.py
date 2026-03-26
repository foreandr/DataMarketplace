"""Jsonify for _goodwork_jobs."""
from __future__ import annotations

import re
from typing import Any, List


_PROVINCES = {
    "BC", "AB", "SK", "MB", "ON", "QC", "NB", "NS", "PE", "NL", "NT", "NU", "YT"
}


def _normalize_details(details: str) -> list[str]:
    text = details.strip()
    if text.startswith(","):
        text = text[1:].strip()
    parts = [p.strip() for p in text.split(",") if p.strip()]
    return parts


def _extract_location(parts: list[str]) -> str:
    if not parts:
        return ""
    return parts[-1]


def _parse_location(location_raw: str) -> tuple[str, str, str]:
    if not location_raw:
        return "", "", ""
    text = location_raw.strip()
    city = text.split(",")[0].strip() if "," in text else text.split("/")[0].strip()
    province = ""
    tokens = re.split(r"[,\s/]+", text)
    for tok in tokens:
        if tok.upper() in _PROVINCES:
            province = tok.upper()
            break
    country = "Canada"
    return city, province, country


def _parse_work_mode(parts: list[str], location_raw: str) -> str:
    joined = " ".join(parts).lower() + " " + location_raw.lower()
    if "remote" in joined:
        return "Remote"
    if "hybrid" in joined:
        return "Hybrid"
    if "onsite" in joined or "on-site" in joined or "on site" in joined:
        return "On-site"
    return ""


def _parse_job_type(parts: list[str]) -> str:
    for part in parts:
        if "full-time" in part.lower():
            return "Full-time"
        if "part-time" in part.lower():
            return "Part-time"
        if "contract" in part.lower():
            return "Contract"
        if "seasonal" in part.lower():
            return "Seasonal"
        if "intern" in part.lower():
            return "Intern"
        if "volunteer" in part.lower() or "vol./board" in part.lower():
            return "Volunteer"
    return ""


def _extract_job_id(url: str) -> str:
    if not url:
        return ""
    m = re.search(r"-(\d+)$", url)
    if m:
        return m.group(1)
    return url


class GoodworkJobsJsonify:
    def __init__(self, source_name: str = "_goodwork_jobs"):
        self.source_name = source_name

    def to_json(self, data: Any, location: dict | None = None) -> List[dict]:
        if not isinstance(data, list):
            return []

        records: list[dict] = []
        for row in data:
            if not isinstance(row, list) or len(row) < 3:
                continue
            title = str(row[0]).strip()
            details = str(row[1]).strip() if len(row) > 1 else ""
            url = str(row[2]).strip() if len(row) > 2 else ""
            if not url.startswith("/"):
                continue
            url = "https://www.goodwork.ca" + url

            parts = _normalize_details(details)
            location_raw = _extract_location(parts)
            work_mode = _parse_work_mode(parts, location_raw)
            job_type = _parse_job_type(parts)
            company = ""
            if len(parts) >= 2:
                company = parts[-2]

            city, province, country = _parse_location(location_raw)
            job_id = _extract_job_id(url)

            record = {
                "id": job_id,
                "title": title,
                "company": company,
                "location_raw": location_raw,
                "work_mode": work_mode,
                "job_type": job_type,
                "url": url,
                "city": city,
                "province": province,
                "country": country,
            }
            if location:
                record["city"] = location.get("city", record["city"])
                record["country"] = location.get("country", record["country"])
            records.append(record)
        return records

    def run_analysis(
        self,
        data: Any,
        location: dict | None = None,
        print_samples: bool = False,
    ) -> List[dict]:
        cleaned = self.to_json(data, location=location)
        if print_samples:
            for rec in cleaned[:10]:
                print(rec)
        return cleaned
