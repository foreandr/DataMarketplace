"""Jsonify for _saskjobs."""
from __future__ import annotations

import re
from typing import Any, List


def _extract_job_id(url: str) -> str:
    if not url:
        return ""
    m = re.search(r"job_order_id=(\d+)", url)
    if m:
        return m.group(1)
    return url


class SaskjobsJsonify:
    def __init__(self, source_name: str = "_saskjobs"):
        self.source_name = source_name

    def to_json(self, data: Any, location: dict | None = None) -> List[dict]:
        if not isinstance(data, list):
            return []

        records: list[dict] = []
        for row in data:
            if not isinstance(row, list) or len(row) < 7:
                continue
            title = str(row[0]).strip()
            noc_code = str(row[1]).strip() if len(row) > 1 else ""
            company = str(row[2]).strip() if len(row) > 2 else ""
            location_raw = str(row[3]).strip() if len(row) > 3 else ""
            posted_date = str(row[4]).strip() if len(row) > 4 else ""
            job_number = str(row[5]).strip() if len(row) > 5 else ""
            url = str(row[6]).strip() if len(row) > 6 else ""
            if not url.startswith("/jsp/joborder/detail.jsp"):
                continue
            url = "https://www.saskjobs.ca" + url

            job_id = _extract_job_id(url)
            city = location_raw.title() if location_raw.isupper() else location_raw

            record = {
                "id": job_id,
                "title": title,
                "company": company,
                "location_raw": location_raw,
                "noc_code": noc_code,
                "posted_date": posted_date,
                "job_number": job_number,
                "is_new": 0,
                "url": url,
                "city": city,
                "province": "SK",
                "country": "Canada",
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
