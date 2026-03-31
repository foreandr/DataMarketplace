"""Jsonify for _indeed_jobs."""
from __future__ import annotations

import re
import json
from datetime import datetime
from typing import Any, List

try:
    from _indeed_jobs.schema import SCHEMA
except ModuleNotFoundError:
    import sys
    from pathlib import Path
    ROOT_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT_DIR / "src"))
    from _indeed_jobs.schema import SCHEMA




class IndeedJobsJsonify:
    def __init__(self, source_name: str = "_indeed_jobs"):
        self.source_name = source_name

    def _extract_url_info(self, item: list) -> tuple[str | None, str | None]:
        for tok in item:
            if not isinstance(tok, str):
                continue
            
            # Organic links
            if 'jk=' in tok:
                match = re.search(r'jk=([a-zA-Z0-9]+)', tok)
                if match:
                    job_id = match.group(1)
                    return f"https://ca.indeed.com/viewjob?jk={job_id}", job_id

            # Sponsored/Ad links
            if '/pagead/clk' in tok:
                # Extract xkcb or similar unique id from the ad string to use as a stable ID
                match = re.search(r'xkcb=([a-zA-Z0-9_-]+)', tok)
                job_id = match.group(1) if match else None
                
                # If no xkcb, hash the token to create a unique ID
                if not job_id:
                    import hashlib
                    job_id = hashlib.md5(tok.encode()).hexdigest()[:16]
                
                full_url = f"https://ca.indeed.com{tok}" if tok.startswith('/') else tok
                return full_url, job_id

        return None, None

    def _parse_pay(self, item: list) -> dict:
        pay_info = {"pay_raw": None, "pay_min": None, "pay_max": None, "pay_period": None}
        pay_pat = re.compile(r'[\d,]+(?:\.\d+)?')
        for tok in item:
            if not isinstance(tok, str): continue
            if '$' in tok and any(p in tok.lower() for p in ['year', 'hour', 'month', 'week', 'day']):
                pay_info["pay_raw"] = tok.strip()
                nums = [float(n.replace(',', '')) for n in pay_pat.findall(tok) if n.replace(',', '')]
                if nums:
                    pay_info["pay_min"] = min(nums)
                    pay_info["pay_max"] = max(nums)
                t_low = tok.lower()
                if 'hour' in t_low: pay_info["pay_period"] = "hour"
                elif 'year' in t_low: pay_info["pay_period"] = "year"
                elif 'month' in t_low: pay_info["pay_period"] = "month"
                elif 'week' in t_low: pay_info["pay_period"] = "week"
                elif 'day' in t_low: pay_info["pay_period"] = "day"
                return pay_info
        return pay_info

    def _extract_location(self, item: list) -> tuple[str | None, str | None, str | None]:
        prov_pat = re.compile(r',\s*([A-Z]{2})(?:\s+[A-Z]\d[A-Z]\s+\d[A-Z]\d)?')
        for i in range(1, min(6, len(item))):
            tok = item[i]
            if not isinstance(tok, str): continue
            match = prov_pat.search(tok)
            if match:
                province = match.group(1)
                city_part = tok.split(',')[0]
                city = re.sub(r'remote\s+in\s+', '', city_part, flags=re.I).strip()
                return tok.strip(), city, province
        return None, None, None

    def to_json(self, data: Any, location: dict | None = None) -> List[dict]:
        if not data or not isinstance(data, list):
            return []

        cleaned_records = []
        noise_badges = {'New', 'Urgently hiring', 'Urgently Hiring', 'Often responds within 1 day', 'Often responds within 3 days', '90+ min', '·'}
        
        for item in data:
            if not isinstance(item, list) or len(item) < 3:
                continue

            try:
                url, job_id = self._extract_url_info(item)
                if not job_id:
                    print(f"Skipping: Still No ID -> {item[:2]}")
                    continue

                pay_data = self._parse_pay(item)
                loc_raw, city, province = self._extract_location(item)
                
                joined = " ".join(str(x) for x in item).lower()
                is_easy = 1 if any(x in joined for x in ['easily apply', 'easy apply']) else 0
                
                job_type = None
                if 'full-time' in joined: job_type = 'Full-time'
                elif 'contract' in joined: job_type = 'Contract'
                elif 'permanent' in joined: job_type = 'Permanent'
                
                title = item[0]
                
                # Dynamic company lookup to skip variable badges
                company = "Unknown"
                for i in range(1, 4):
                    if i < len(item) and item[i] not in noise_badges and len(item[i]) > 2:
                        # Ensure we don't pick the location string as company
                        if ',' not in item[i]:
                            company = item[i]
                            break

                record = {
                    "id": job_id,
                    "title": title,
                    "company": company,
                    "location_raw": loc_raw,
                    "pay_raw": pay_data["pay_raw"],
                    "pay_min": pay_data["pay_min"],
                    "pay_max": pay_data["pay_max"],
                    "pay_period": pay_data["pay_period"],
                    "job_type": job_type,
                    "schedule": None, 
                    "benefits": None, 
                    "is_easy_apply": is_easy,
                    "posted_date": datetime.now().strftime("%Y-%m-%d"),
                    "url": url,
                    "city": city or (location or {}).get('city'),
                    "province": province or (location or {}).get('province'),
                    "country": (location or {}).get('country', 'Canada'),
                    "crawled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                final_record = {k: record.get(k) for k in SCHEMA.field_names()}
                cleaned_records.append(final_record)

            except Exception as e:
                continue

        return cleaned_records

    def run_analysis(self, data: Any, location: dict | None = None, print_samples: bool = False) -> List[dict]:
        results = self.to_json(data, location=location)
        return results