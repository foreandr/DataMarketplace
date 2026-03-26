"""Jsonify for _charityvillage_jobs."""
from __future__ import annotations

import re
from typing import Any, List


_PROVINCES = {
    "BC", "AB", "SK", "MB", "ON", "QC", "NB", "NS", "PE", "NL", "NT", "NU", "YT"
}


def _next_value(row: list[str], label: str) -> str:
    try:
        idx = row.index(label)
    except ValueError:
        return ""
    if idx + 1 >= len(row):
        return ""
    return str(row[idx + 1]).strip()


def _first_job_url(row: list[str]) -> str:
    for item in row:
        if isinstance(item, str) and item.startswith("/job/"):
            return "https://www.charityvillage.com" + item
    for item in row:
        if isinstance(item, str) and item.startswith("http"):
            return item
    return ""


def _extract_job_id(url: str) -> str:
    if not url:
        return ""
    m = re.search(r"/job/[^/]*-(\d+)", url)
    if m:
        return m.group(1)
    return url


def _parse_location(location_raw: str) -> tuple[str, str, str]:
    if not location_raw:
        return "", "", ""
    text = location_raw.replace("\n", ",").strip()
    city = text.split(",")[0].strip()
    province = ""
    tokens = re.split(r"[,\s]+", text)
    for tok in tokens:
        if tok.upper() in _PROVINCES:
            province = tok.upper()
            break
    country = "Canada" if "canada" in text.lower() or province else "Canada"
    return city, province, country


class CharityvillageJobsJsonify:
    def __init__(self, source_name: str = "_charityvillage_jobs"):
        self.source_name = source_name

    def to_json(self, data: Any, location: dict | None = None) -> List[dict]:
        if not isinstance(data, list):
            return []

        records: list[dict] = []
        for row in data:
            if not isinstance(row, list) or len(row) < 2:
                continue
            title = str(row[0]).strip()
            company = str(row[1]).strip() if len(row) > 1 else ""
            location_raw = _next_value(row, "location")
            work_mode = _next_value(row, "remote")
            posted_date = _next_value(row, "Published")
            expires_date = _next_value(row, "Expires")
            salary_raw = _next_value(row, "salary")
            is_quick_apply = 1 if any(str(x).strip().lower() == "quick apply" for x in row) else 0
            url = _first_job_url(row)
            job_id = _extract_job_id(url)

            city, province, country = _parse_location(location_raw)

            record = {
                "id": job_id,
                "title": title,
                "company": company,
                "location_raw": location_raw,
                "work_mode": work_mode,
                "job_type": "",
                "salary_raw": salary_raw,
                "posted_date": posted_date,
                "expires_date": expires_date,
                "is_quick_apply": is_quick_apply,
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
