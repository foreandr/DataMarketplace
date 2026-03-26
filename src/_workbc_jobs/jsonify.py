"""Jsonify for _workbc_jobs."""
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


def _first_url(row: list[str]) -> str:
    for item in row:
        if isinstance(item, str) and item.startswith("https://api-jobboard.workbc.ca/Print/Job?jobid="):
            return item
    for item in row:
        if isinstance(item, str) and item.startswith("http"):
            return item
    for item in row:
        if isinstance(item, str) and item.startswith("/search-and-prepare-job/find-jobs#/job-details/"):
            return "https://www.workbc.ca" + item
    return ""


def _extract_job_id(job_number: str, url: str) -> str:
    if job_number:
        m = re.search(r"(\d{6,})", job_number)
        if m:
            return m.group(1)
    if url:
        m = re.search(r"jobid=(\d+)", url)
        if m:
            return m.group(1)
        m = re.search(r"/job-details/(\d+)", url)
        if m:
            return m.group(1)
    return ""


def _parse_views(row: list[str]) -> int | None:
    for item in row:
        if isinstance(item, str) and "views" in item.lower():
            m = re.search(r"(\d+)", item)
            if m:
                return int(m.group(1))
    return None


def _parse_location(location_raw: str) -> tuple[str, str, str]:
    if not location_raw:
        return "", "", ""
    text = location_raw.strip()
    city = text.split(",")[0].strip()
    province = ""
    tokens = re.split(r"[,\s]+", text)
    for tok in tokens:
        if tok.upper() in _PROVINCES:
            province = tok.upper()
            break
    country = "Canada" if "canada" in text.lower() or province else "Canada"
    return city, province, country


def _parse_work_mode(row: list[str], location_raw: str) -> str:
    candidates = ("remote", "hybrid", "onsite", "on-site", "on site", "work remotely")
    joined = " ".join([str(x) for x in row if isinstance(x, str)]).lower()
    if "remote" in joined:
        return "Remote"
    if "hybrid" in joined:
        return "Hybrid"
    if "on-site" in joined or "onsite" in joined or "on site" in joined:
        return "On-site"
    if "remote" in location_raw.lower():
        return "Remote"
    return ""


def _parse_date(value: str) -> str:
    if not value:
        return ""
    value = value.strip()
    return value if re.match(r"\d{4}-\d{2}-\d{2}$", value) else value


class WorkbcJobsJsonify:
    def __init__(self, source_name: str = "_workbc_jobs"):
        self.source_name = source_name

    def to_json(self, data: Any, location: dict | None = None) -> List[dict]:
        if not isinstance(data, list):
            return []

        records: list[dict] = []
        for row in data:
            if not isinstance(row, list) or not row:
                continue
            title = str(row[1]).strip() if len(row) > 1 else ""
            company = str(row[2]).strip() if len(row) > 2 else ""

            location_raw = _next_value(row, "Location:")
            salary_raw = _next_value(row, "Salary:")
            job_type = _next_value(row, "Job Type:")
            job_number = ""
            for item in row:
                if isinstance(item, str) and item.startswith("Job Number:"):
                    job_number = item.replace("Job Number:", "").strip()
                    break
            views = _parse_views(row)
            posted_date = _parse_date(_next_value(row, "Posted:"))
            updated_date = _parse_date(_next_value(row, "Last Updated:"))
            expires_date = _parse_date(_next_value(row, "Expires:"))
            url = _first_url(row)

            work_mode = _parse_work_mode(row, location_raw)
            city, province, country = _parse_location(location_raw)
            job_id = _extract_job_id(job_number, url)
            if not job_id and url:
                job_id = url

            record = {
                "id": job_id,
                "title": title,
                "company": company,
                "location_raw": location_raw,
                "work_mode": work_mode,
                "salary_raw": salary_raw,
                "job_type": job_type,
                "job_number": job_number,
                "views": views if views is not None else None,
                "posted_date": posted_date,
                "updated_date": updated_date,
                "expires_date": expires_date,
                "url": url,
                "city": city,
                "province": province,
                "country": country,
            }
            # Optional location override
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
