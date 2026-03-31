"""Jsonify for _jobspider_jobs."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, List

try:
    from _jobspider_jobs.schema import SCHEMA
except ModuleNotFoundError:
    import sys
    from pathlib import Path
    ROOT_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT_DIR / "src"))
    from _jobspider_jobs.schema import SCHEMA


# US state codes + Canadian province codes
_US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
    "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
    "VA","WA","WV","WI","WY","DC",
}
_CA_PROVINCES = {
    "BC","AB","SK","MB","ON","QC","NB","NS","PE","NL","NT","NU","YT",
}


def _extract_id(url: str) -> str:
    """Pull the trailing numeric ID from a jobspider URL."""
    if not url:
        return ""
    m = re.search(r"-(\d+)$", url.strip())
    return m.group(1) if m else url.strip()


def _parse_location(location_raw: str) -> tuple[str, str, str]:
    """Return (city, state_or_province, country) from 'City, ST' string."""
    if not location_raw:
        return "", "", ""
    text = location_raw.strip().replace("\xa0", " ")
    parts = [p.strip() for p in text.split(",")]
    city = parts[0] if parts else ""
    code = parts[1].strip().upper() if len(parts) > 1 else ""
    if code in _US_STATES:
        return city, code, "United States"
    if code in _CA_PROVINCES:
        return city, code, "Canada"
    return city, code, ""


def _parse_added_field(added_str: str) -> tuple[str, str]:
    """
    Parse:
      'Added - 3/30/2026 8:49:10 AM PST to Information Technology'
      'Added - Tuesday, March 31, 2026'
    Returns (posted_date, category).
    """
    if not added_str:
        return "", ""
    text = added_str.strip()

    # Split on " to " to isolate category
    if " to " in text:
        date_part, category = text.rsplit(" to ", 1)
        category = category.strip()
    else:
        date_part, category = text, ""

    # Strip "Added - " prefix
    date_part = re.sub(r"^Added\s*[-–]\s*", "", date_part, flags=re.I).strip()

    # Strip leading weekday name e.g. "Tuesday, "
    date_part = re.sub(r"^[A-Za-z]+,\s*", "", date_part).strip()

    return date_part, category


class JobspiderJobsJsonify:
    def __init__(self, source_name: str = "_jobspider_jobs"):
        self.source_name = source_name

    def to_json(self, data: Any) -> List[dict]:
        if not isinstance(data, list):
            return []

        records: list[dict] = []

        for row in data:
            if not isinstance(row, list) or len(row) < 5:
                continue

            try:
                is_sponsored = 1 if "Sponsored" in row else 0

                if is_sponsored:
                    # Sponsored rows are positionally shifted — anchor on "Sponsored"
                    sp_idx = row.index("Sponsored")
                    title        = " ".join(str(x).strip() for x in row[:sp_idx]).strip()
                    company      = str(row[sp_idx + 1]).strip() if sp_idx + 1 < len(row) else ""
                    location_raw = str(row[sp_idx + 2]).strip() if sp_idx + 2 < len(row) else ""
                    description  = str(row[sp_idx + 3]).strip() if sp_idx + 3 < len(row) else ""
                    added_str    = next((str(x) for x in row if isinstance(x, str) and "Added" in x), "")
                    url          = str(row[-1]).strip()
                else:
                    # Normal row: [title, company, location, description, added_str, url]
                    title        = str(row[0]).strip()
                    company      = str(row[1]).strip().replace("\xa0", " ")
                    location_raw = str(row[2]).strip()
                    description  = str(row[3]).strip() if len(row) > 3 else ""
                    added_str    = str(row[4]).strip() if len(row) > 4 else ""
                    url          = str(row[5]).strip() if len(row) > 5 else ""

                if not url:
                    continue

                posted_date, category = _parse_added_field(added_str)
                city, province, country = _parse_location(location_raw)
                job_id = _extract_id(url)

                record = {
                    "id":           job_id,
                    "title":        title,
                    "company":      company,
                    "location_raw": location_raw,
                    "category":     category,
                    "posted_date":  posted_date,
                    "is_sponsored": is_sponsored,
                    "description":  description,
                    "url":          url,
                    "city":         city,
                    "province":     province,
                    "country":      country,
                    "crawled_at":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }

                records.append({k: record.get(k) for k in SCHEMA.field_names()})

            except Exception as exc:
                print(f"  [jsonify skip] {exc} | row={row[:3]}")
                continue

        return records

    def run_analysis(
        self,
        data: Any,
        print_samples: bool = False,
    ) -> List[dict]:
        cleaned = self.to_json(data)
        if print_samples:
            for rec in cleaned[:10]:
                print(rec)
        return cleaned
