"""Jsonify for _canadian_jobbank."""
from __future__ import annotations

import json
import random
import re
from datetime import datetime
from typing import Any, List

try:
    from _canadian_jobbank.schema import SCHEMA
except ModuleNotFoundError:
    import sys
    from pathlib import Path
    ROOT_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT_DIR / "src"))
    from _canadian_jobbank.schema import SCHEMA

GREEN = "\033[92m"
RED   = "\033[91m"
RESET = "\033[0m"
BOLD  = "\033[1m"
CY    = "\033[96m"

BASE_URL   = "https://www.jobbank.gc.ca"
MAX_HOURLY = 120.0

# ── known noise tokens to skip entirely ───────────────────────────────────────
_SKIP_TOKENS = {
    'Location', 'Job number:', 'Your favourites', 'Sign in',
    'Sign up for a Plus account', 'Posted on Job Bank', 'Job Bank',
    'This job was posted directly by the employer on Job Bank.',
    'New', 'On site', 'On-site', 'Remote', 'Hybrid',
    'CareerBeacon', 'Jobillico', 'indeed.com', 'Direct Apply',
    'LMIA approved',
}

# ── regex ──────────────────────────────────────────────────────────────────────
_URL_PAT  = re.compile(r'/jobsearch/jobposting/(\d+)', re.IGNORECASE)
_DATE_PAT = re.compile(
    r'(?:january|february|march|april|may|june|july|august|september|october|november|december)'
    r'\s+\d{1,2},?\s+\d{4}',
    re.IGNORECASE,
)
_MONTH_MAP = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12,
}
_PROVINCES = {
    'AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'NT', 'NU',
    'ON', 'PE', 'QC', 'SK', 'YT',
}


class CanadianJobbankJsonify:
    def __init__(self, source_name: str = "_canadian_jobbank", debug: bool = False):
        self.source_name     = source_name
        self.debug           = debug
        self.processed_count = 0
        self.skipped_count   = 0
        self.skipped_data:  List[dict] = []
        self.success_data:  List[dict] = []

    # ── field extractors ──────────────────────────────────────────────────────

    def _extract_url_and_id(self, item: list) -> tuple[str | None, str | None]:
        for tok in item:
            if not isinstance(tok, str):
                continue
            m = _URL_PAT.search(tok)
            if m:
                job_id = m.group(1)
                full   = f"{BASE_URL}/jobsearch/jobposting/{job_id}"
                return full, job_id
        return None, None

    def _extract_location(self, item: list) -> tuple[str | None, str | None, str | None]:
        """Return (location_raw, city, province) using the 'Location' anchor."""
        try:
            idx = item.index('Location')
            raw = item[idx + 1].strip() if idx + 1 < len(item) else None
        except ValueError:
            raw = None

        if not raw:
            return None, None, None

        # 'Toronto (ON)'  or  'London, ON'
        m = re.match(r'^(.+?)\s*[\(,]\s*([A-Z]{2})\s*\)?$', raw)
        if m:
            city = m.group(1).strip()
            prov = m.group(2).upper()
            if prov in _PROVINCES:
                return raw, city, prov
        return raw, None, None

    def _extract_pay(self, item: list) -> float | None:
        """Find the 'Salary\\n...' token and parse an hourly rate from it."""
        for tok in item:
            if not isinstance(tok, str) or not tok.startswith('Salary'):
                continue
            # e.g. "Salary\n\t\t\t\t\t\t$36.00 hourly"
            #   or "Salary\n\t\t\t\t\t\t$43.75 to $103.37 hourly"
            #   or "Salary\n\t\t\t\t\t\t$85,000.00 to $95,000.00 annually"
            is_annual  = bool(re.search(r'annual|yearly|year', tok, re.IGNORECASE))
            is_weekly  = bool(re.search(r'weekly|biweekly', tok, re.IGNORECASE))
            if is_annual or is_weekly:
                return None

            nums = [float(n.replace(',', ''))
                    for n in re.findall(r'[\d,]+(?:\.\d+)?', tok)
                    if n.replace(',', '')]
            if not nums:
                return None
            val = round(sum(nums) / len(nums), 2)
            return val if val <= MAX_HOURLY else None
        return None

    def _extract_date(self, item: list) -> str:
        now = datetime.now()
        for tok in item:
            if not isinstance(tok, str):
                continue
            m = _DATE_PAT.search(tok)
            if not m:
                continue
            ds = m.group(0)
            parts = ds.replace(',', '').split()
            try:
                month = _MONTH_MAP[parts[0].lower()]
                day   = int(parts[1])
                year  = int(parts[2])
                return datetime(year, month, day).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
        return now.strftime("%Y-%m-%d %H:%M:%S")

    def _extract_flags(self, item: list) -> tuple[int, int]:
        joined = " ".join(str(x) for x in item).lower()
        is_lmia         = 1 if 'lmia' in joined else 0
        is_direct_apply = 1 if 'direct apply' in joined else 0
        return is_lmia, is_direct_apply

    def _extract_work_mode(self, item: list) -> str | None:
        for tok in item:
            if not isinstance(tok, str):
                continue
            t = tok.strip().lower()
            if t in ('on site', 'on-site', 'onsite'):
                return 'on_site'
            if t == 'remote':
                return 'remote'
            if t == 'hybrid':
                return 'hybrid'
        return None

    def _extract_source(self, item: list) -> str | None:
        _known = {
            'careerbeacon':   'CareerBeacon',
            'jobillico':      'Jobillico',
            'indeed.com':     'indeed.com',
            'job bank':       'Job Bank',
            'saskjobs':       'SaskJobs',
            'québec emploi':  'Quebec Emploi',
            'quebec emploi':  'Quebec Emploi',
            'workinbc':       'WorkInBC',
            'alborsa':        'Alborsa',
        }
        for tok in item:
            if not isinstance(tok, str):
                continue
            key = tok.strip().lower()
            if key in _known:
                return _known[key]
        return None

    def _extract_title_and_company(self, item: list) -> tuple[str | None, str | None]:
        """
        Structure is always:
          [badges...] TITLE  DATE  COMPANY  'Location'  ...

        So: find the date index, title is the last real token before it,
        company is the first real token after it (before 'Location').
        """
        date_idx = next(
            (i for i, tok in enumerate(item)
             if isinstance(tok, str) and _DATE_PAT.search(tok)),
            None,
        )
        if date_idx is None:
            return None, None

        # Title: scan backwards from date, skip noise
        title = None
        for tok in reversed(item[:date_idx]):
            if not isinstance(tok, str):
                continue
            t = tok.strip()
            if t in _SKIP_TOKENS or not t:
                continue
            title = t
            break

        # Company: scan forwards from date, stop at 'Location'
        company = None
        for tok in item[date_idx + 1:]:
            if not isinstance(tok, str):
                continue
            t = tok.strip()
            if t == 'Location':
                break
            if t in _SKIP_TOKENS or not t:
                continue
            company = t
            break

        return title, company

    # ── main API ──────────────────────────────────────────────────────────────

    def to_json(self, data: Any) -> List[dict]:
        self.processed_count = 0
        self.skipped_count   = 0
        self.skipped_data    = []
        self.success_data    = []

        if not data or not isinstance(data, list):
            return []

        for item in data:
          try:
            if not isinstance(item, list):
                self.skipped_count += 1
                self.skipped_data.append({"reason": "Not a list", "raw": str(item)})
                continue

            url, job_id = self._extract_url_and_id(item)
            if not url:
                self.skipped_count += 1
                self.skipped_data.append({"reason": "No job URL found", "raw": item})
                continue

            pay = self._extract_pay(item)
            if pay is None:
                self.skipped_count += 1
                self.skipped_data.append({"reason": "No hourly pay found", "raw": item})
                continue

            title, company = self._extract_title_and_company(item)
            if not title or len(title.strip()) < 3:
                self.skipped_count += 1
                self.skipped_data.append({"reason": "Title missing/too short", "raw": item})
                continue

            location_raw, city, prov = self._extract_location(item)
            is_lmia, is_direct_apply = self._extract_flags(item)

            record = {
                "id":              job_id,
                "title":           title,
                "company":         company,
                "location_raw":    location_raw,
                "posted_date":     self._extract_date(item),
                "pay":             pay,
                "is_lmia":         is_lmia,
                "is_direct_apply": is_direct_apply,
                "work_mode":       self._extract_work_mode(item),
                "source":          self._extract_source(item),
                "url":             url,
                "city":            city,
                "state":           prov,
                "country":         "Canada",
            }
            self.success_data.append({k: record.get(k) for k in SCHEMA.field_names()})
            self.processed_count += 1

          except Exception as e:
            self.skipped_count += 1
            self.skipped_data.append({"reason": f"Unexpected error: {e}", "raw": item})

        return self.success_data

    def run_analysis(self, data: Any, print_samples: bool = False) -> List[dict]:
        results = self.to_json(data)

        if not print_samples:
            return results

        if self.success_data:
            num = min(8, len(self.success_data))
            print(f"\n{BOLD}--- SUCCESS DATA ({num} RANDOM SAMPLES) ---{RESET}")
            for rec in random.sample(self.success_data, num):
                print(f"{GREEN}{json.dumps(rec, indent=2, ensure_ascii=True)}{RESET}")

        if self.skipped_data:
            num_fail = min(8, len(self.skipped_data))
            print(f"\n{BOLD}--- FAILED DATA ({num_fail} RANDOM SAMPLES) ---{RESET}")
            for fail in random.sample(self.skipped_data, num_fail):
                print(f"{RED}REASON: {fail['reason']}{RESET}")
                print(f"{RED}DATA  : {str(fail.get('raw', ''))[:300]}{RESET}\n")

        total = self.processed_count + self.skipped_count
        rate  = (self.processed_count / total * 100) if total > 0 else 0
        print(
            f"\n{BOLD}{'='*40}\nANALYSIS COMPLETE\n"
            f"Items Processed: {GREEN}{self.processed_count}{RESET}\n"
            f"Items Skipped:   {RED}{self.skipped_count}{RESET}\n"
            f"Success Rate:    {BOLD}{rate:.1f}%{RESET}\n"
            f"{'='*40}{RESET}"
        )
        return results
