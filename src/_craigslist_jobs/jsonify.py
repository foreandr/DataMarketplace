"""Jsonify for _craigslist_jobs."""
from __future__ import annotations

import json
import random
import re
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, List

try:
    from _craigslist_jobs.schema import SCHEMA
except ModuleNotFoundError:
    import sys
    from pathlib import Path
    ROOT_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT_DIR / "src"))
    from _craigslist_jobs.schema import SCHEMA

from _craigslist_jobs.demo_data import DEMO_DATA

GREEN = "\033[92m"
RED   = "\033[91m"
RESET = "\033[0m"
BOLD  = "\033[1m"
YL    = "\033[93m"
CY    = "\033[96m"

# ── regex helpers ──────────────────────────────────────────────────────────────
_DATE_PAT    = re.compile(r'^\d{1,2}/\d{1,2}$')
_PAY_PAT     = re.compile(
    r'(\$|\d+\s*/\s*hr|per\s+hour|per\s+week|per\s+year|per\s+mile'
    r'|/hour|weekly|hourly|annually|annual|salary|cpm|cents\s+per'
    r'|competitive|negotiable|tbd|boe|tbdboe'
    r'|to\s+be\s+discussed|based\s+on\s+exp|doe|doh|commensurate'
    r'|flex|home\s+time|home\s+daily|home\s+weekly'
    r'|\d+\s*(?:an\s+hour|a\s+week|a\s+year|per\s+shift)'
    r'|%\s+(?:of|line)|gross|earn\s+\d)',
    re.IGNORECASE,
)
_URL_PAT     = re.compile(r'https?://')
_IMG_PAT     = re.compile(r'images\.craigslist\.org|craigslist\.org/images|empty\.png', re.IGNORECASE)
_LISTING_URL = re.compile(r'craigslist\.org.*?/d/', re.IGNORECASE)
# Common company suffixes — helps distinguish employer from location
_COMPANY_PAT = re.compile(
    r'\b(llc|inc\.?|corp\.?|ltd\.?|co\.|company|services|group|management'
    r'|logistics|solutions|associates|enterprises|staffing|systems|agency'
    r'|agency|industries|international|consulting|transport|trucking'
    r'|express|freight|delivery|movers?|storage)\b',
    re.IGNORECASE,
)
MAX_HOURLY_PAY = 100.0  # anything over this is assumed not to be an hourly rate


class CraigslistJobsJsonify:
    def __init__(self, source_name: str = "_craigslist_jobs", debug: bool = False):
        self.source_name     = source_name
        self.debug           = debug
        self.processed_count = 0
        self.skipped_count   = 0
        self.skipped_data: List[dict] = []
        self.success_data:  List[dict] = []

    # ── field extractors ───────────────────────────────────────────────────────

    def _parse_date(self, date_str: str | None) -> str:
        now = datetime.now()
        if not date_str:
            return now.strftime("%Y-%m-%d %H:%M:%S")
        ds = date_str.strip()
        try:
            if "/" in ds:
                dt = datetime.strptime(f"{ds}/{now.year}", "%m/%d/%Y")
                return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
        return now.strftime("%Y-%m-%d %H:%M:%S")

    def _parse_pay_numeric(self, pay_str: str | None) -> float | None:
        """Extract the first meaningful dollar/number from a pay string."""
        if not pay_str:
            return None
        # Strip currency symbols and try to find a number
        # Prefer higher-end of ranges (e.g. "$20-$30" → 30)
        nums = re.findall(r'[\d]+(?:[.,]\d+)?', pay_str.replace(',', ''))
        if not nums:
            return None
        floats = [float(n) for n in nums]
        # If range, take average
        if len(floats) >= 2 and floats[1] > floats[0]:
            return round((floats[0] + floats[1]) / 2, 2)
        return floats[0] if floats else None

    def _looks_like_pay_range(self, s: str) -> bool:
        """Catch bare numeric ranges like '14-17.50' or '18 24' as pay."""
        return bool(re.match(r'^\$?[\d,]+(?:\.\d+)?\s*[-–to]+\s*\$?[\d,]+(?:\.\d+)?$', s.strip(), re.IGNORECASE))

    def _is_url(self, s: str) -> bool:
        return bool(_URL_PAT.match(s))

    def _is_date(self, s: str) -> bool:
        return bool(_DATE_PAT.match(s.strip()))

    def _is_image_url(self, s: str) -> bool:
        return bool(_IMG_PAT.search(s))

    def _is_listing_url(self, s: str) -> bool:
        return bool(_LISTING_URL.search(s))

    def _is_pay(self, s: str) -> bool:
        return bool(_PAY_PAT.search(s))

    def _parse_row(self, item: list) -> dict | None:
        """
        Convert a raw scraped list into a structured dict.

        Craigslist job rows have variable length (6-9 elements).
        Anchors we can rely on:
          - item[0]  = listing ID (numeric string)
          - URL      = contains craigslist.org/…/d/
          - image    = contains craigslist.org/images or empty.png
          - date     = matches M/D  (e.g. "3/17")
        Everything else (title, location, pay, employer) floats.
        """
        if not isinstance(item, list) or len(item) < 4:
            return None

        id_   = str(item[0])
        url   = next((x for x in item if isinstance(x, str) and self._is_listing_url(x)), None)
        image = next((x for x in item if isinstance(x, str) and self._is_image_url(x)), None)
        date_str = next((x for x in item if isinstance(x, str) and self._is_date(x)), None)

        if url is None:
            return None

        # Build the pool of "middle" tokens — everything that isn't
        # the id, a full URL, or the date.
        used  = {id_, url, image, date_str}
        pool  = [x for x in item[1:] if isinstance(x, str) and x not in used and not self._is_url(x)]

        # ── Title: repeated token wins unconditionally (Craigslist echoes it) ─
        counts  = Counter(pool)
        repeats = [k for k, v in counts.items() if v > 1]
        title   = max(repeats, key=len) if repeats else None

        # Remove title (both copies) from pool before any further extraction
        remaining = list(pool)
        if title:
            for _ in range(counts[title]):
                remaining.remove(title)

        # ── Pay: look in remaining tokens only (title already removed) ───────
        # Prefer shorter tokens that look like pay to avoid pulling in long
        # descriptive titles.  Cap at 80 chars to avoid eating job descriptions.
        pay_str = next(
            (x for x in remaining
             if len(x) <= 80 and (self._is_pay(x) or self._looks_like_pay_range(x))),
            None,
        )
        if pay_str:
            remaining.remove(pay_str)

        # ── Fallback title if there were no repeats ───────────────────────────
        if title is None:
            # Prefer tokens that don't look like company names
            non_company = [x for x in remaining if not _COMPANY_PAT.search(x)]
            candidates  = non_company if non_company else remaining
            title       = max(candidates, key=len) if candidates else None
            if title:
                remaining.remove(title)

        # ── Location vs employer: short simple strings are locations ─────────
        location_str = None
        employer_str = None
        for tok in remaining:
            stripped = tok.strip()
            looks_like_company = bool(_COMPANY_PAT.search(stripped))
            # A location: short, no $, no /, no company suffix, pure alpha/space
            if (
                not looks_like_company
                and len(stripped) <= 30
                and '$' not in stripped
                and '/' not in stripped
                and not re.search(r'\d{5}', stripped)
                and re.match(r'^[A-Za-z0-9\s\.,\-]+$', stripped)
                and location_str is None
            ):
                location_str = stripped
            else:
                if employer_str is None:
                    employer_str = stripped

        return {
            "id":          id_,
            "title":       title,
            "location":    location_str,
            "pay":         self._parse_pay_numeric(pay_str),
            "company":     employer_str,
            "posted_date": self._parse_date(date_str),
            "url":         url,
            "image_url":   image,
        }

    # ── main API ───────────────────────────────────────────────────────────────

    def to_json(self, data: Any, location: dict | None = None) -> List[dict]:
        self.processed_count = 0
        self.skipped_count   = 0
        self.skipped_data    = []
        self.success_data    = []

        if not data or not isinstance(data, list):
            return []

        loc_city    = (location or {}).get("city")
        loc_state   = (location or {}).get("state")
        loc_country = (location or {}).get("country")

        for item in data:
            if not isinstance(item, list):
                self.skipped_count += 1
                self.skipped_data.append({"reason": "Not a list", "raw": str(item)})
                continue

            record = self._parse_row(item)

            if record is None:
                self.skipped_count += 1
                self.skipped_data.append({"reason": "Could not parse row", "raw": item})
                continue

            if not record.get("url"):
                self.skipped_count += 1
                self.skipped_data.append({"reason": "Missing URL", "raw": item})
                continue

            if not record.get("title") or len(record["title"].strip()) < 4:
                self.skipped_count += 1
                self.skipped_data.append({"reason": "Title too short/missing", "raw": item})
                continue

            pay = record.get("pay")
            if pay is None:
                self.skipped_count += 1
                self.skipped_data.append({"reason": "No pay found", "raw": item})
                continue

            if pay > MAX_HOURLY_PAY:
                self.skipped_count += 1
                self.skipped_data.append({"reason": f"Pay ${pay} exceeds hourly cap (${MAX_HOURLY_PAY})", "raw": item})
                continue

            record["city"]    = loc_city
            record["state"]   = loc_state
            record["country"] = loc_country

            # Map to schema fields only
            schema_rec = {k: record.get(k) for k in SCHEMA.field_names()}
            self.success_data.append(schema_rec)
            self.processed_count += 1

        return self.success_data

    def run_analysis(
        self,
        data: Any,
        location: dict | None = None,
        print_samples: bool = False,
    ) -> List[dict]:
        results = self.to_json(data, location=location)

        if not print_samples:
            return results
        
        '''
        if self.success_data:
            num = min(8, len(self.success_data))
            print(f"\n{BOLD}--- SUCCESS DATA ({num} RANDOM SAMPLES) ---{RESET}")
            for rec in random.sample(self.success_data, num):
                print(f"{GREEN}{json.dumps(rec, indent=2, ensure_ascii=True)}{RESET}")
        '''
        '''
        if self.skipped_data:
            num_fail = min(8, len(self.skipped_data))
            print(f"\n{BOLD}--- FAILED DATA ({num_fail} RANDOM SAMPLES) ---{RESET}")
            for fail in random.sample(self.skipped_data, num_fail):
                print(f"{RED}REASON: {fail['reason']}{RESET}")
                print(f"{RED}DATA  : {str(fail.get('raw', ''))[:300]}{RESET}\n")
        '''

        '''
        total = self.processed_count + self.skipped_count
        rate  = (self.processed_count / total * 100) if total > 0 else 0
        print(
            f"\n{BOLD}{'='*40}\nANALYSIS COMPLETE\n"
            f"Items Processed: {GREEN}{self.processed_count}{RESET}\n"
            f"Items Skipped:   {RED}{self.skipped_count}{RESET}\n"
            f"Success Rate:    {BOLD}{rate:.1f}%{RESET}\n"
            f"{'='*40}{RESET}"
        )
        '''
        return results


# ── quick self-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    j = CraigslistJobsJsonify(debug=True)
    results = j.run_analysis(DEMO_DATA, print_samples=True)
    print(f"\n{CY}Total records returned: {len(results)}{RESET}")
