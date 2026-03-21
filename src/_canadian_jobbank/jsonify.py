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

BASE_URL    = "https://www.jobbank.gc.ca"
MAX_HOURLY  = 120.0   # cap — anything over this is annual/salary, skip it

# ── regex ──────────────────────────────────────────────────────────────────────
_URL_PAT    = re.compile(r'/jobsearch/jobposting/(\d+)', re.IGNORECASE)
_FULL_URL   = re.compile(r'https?://.*jobbank.*jobposting/\d+', re.IGNORECASE)
_PAY_PAT    = re.compile(
    r'\$[\d,]+(?:\.\d+)?\s*(?:to|-)\s*\$[\d,]+(?:\.\d+)?\s*(?:hourly|weekly|annually|biweekly|monthly)?'
    r'|\$[\d,]+(?:\.\d+)?\s*(?:hourly|per\s+hour|/hr|/h)',
    re.IGNORECASE,
)
_DATE_PAT   = re.compile(
    r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}'
    r'|\d{4}-\d{2}-\d{2}'
    r'|\d{1,2}/\d{1,2}/\d{2,4}',
    re.IGNORECASE,
)
_MONTH_MAP  = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}
# Canadian province abbreviations
_PROVINCES  = {
    'AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'NT', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT',
}


class CanadianJobbankJsonify:
    def __init__(self, source_name: str = "_canadian_jobbank", debug: bool = False):
        self.source_name     = source_name
        self.debug           = debug
        self.processed_count = 0
        self.skipped_count   = 0
        self.skipped_data:  List[dict] = []
        self.success_data:  List[dict] = []

    # ── field parsers ──────────────────────────────────────────────────────────

    def _extract_url_and_id(self, item: list) -> tuple[str | None, str | None]:
        """Return (full_url, job_id) from a raw row."""
        for tok in item:
            if not isinstance(tok, str):
                continue
            # Already a full URL
            if _FULL_URL.search(tok):
                m = _URL_PAT.search(tok)
                return tok.split('?')[0], (m.group(1) if m else None)
            # Relative path only
            m = _URL_PAT.search(tok)
            if m:
                path = m.group(0)
                return f"{BASE_URL}{path}", m.group(1)
        return None, None

    def _parse_pay(self, item: list) -> float | None:
        """Extract hourly rate. Returns None if not hourly or not parseable."""
        for tok in item:
            if not isinstance(tok, str):
                continue
            m = _PAY_PAT.search(tok)
            if not m:
                continue
            pay_str = m.group(0)
            is_hourly = bool(re.search(r'hourly|per\s+hour|/hr|/h', pay_str, re.IGNORECASE))
            is_annual = bool(re.search(r'annual|yearly|year', pay_str, re.IGNORECASE))
            is_weekly = bool(re.search(r'weekly|biweekly', pay_str, re.IGNORECASE))
            # If no unit at all, treat as hourly (most common on Job Bank)
            if is_annual or is_weekly:
                return None   # skip non-hourly

            nums = [float(n.replace(',', '')) for n in re.findall(r'[\d,]+(?:\.\d+)?', pay_str)]
            if not nums:
                return None
            # Range → average
            val = round(sum(nums) / len(nums), 2) if len(nums) >= 2 else nums[0]
            return val if val <= MAX_HOURLY else None
        return None

    def _parse_date(self, item: list) -> str:
        now = datetime.now()
        for tok in item:
            if not isinstance(tok, str):
                continue
            m = _DATE_PAT.search(tok)
            if not m:
                continue
            ds = m.group(0).strip()
            try:
                # "March 15, 2026" or "Mar 15 2026"
                month_word = re.match(r'([a-z]+)', ds, re.IGNORECASE)
                if month_word:
                    nums = re.findall(r'\d+', ds)
                    if len(nums) >= 2:
                        month = _MONTH_MAP.get(month_word.group(1)[:3].lower(), 1)
                        day   = int(nums[0]) if int(nums[0]) <= 31 else int(nums[1])
                        year  = int(nums[-1]) if int(nums[-1]) > 100 else now.year
                        return datetime(year, month, day).strftime("%Y-%m-%d %H:%M:%S")
                # ISO or slash formats
                for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
                    try:
                        return datetime.strptime(ds[:10], fmt).strftime("%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass
            except Exception:
                pass
        return now.strftime("%Y-%m-%d %H:%M:%S")

    def _parse_location(self, item: list) -> tuple[str | None, str | None, str | None]:
        """Return (location_raw, city, province)."""
        for tok in item:
            if not isinstance(tok, str):
                continue
            tok = tok.strip()
            # Skip things that look like job titles, pay strings, or URLs
            if _PAY_PAT.search(tok) or '/' in tok or len(tok) > 60:
                continue
            # Look for "City, AB" or "City, Ontario" pattern
            m = re.search(r'^(.+?),\s*([A-Z]{2})\s*$', tok)
            if m:
                city = m.group(1).strip()
                prov = m.group(2).upper()
                if prov in _PROVINCES:
                    return tok, city, prov
            # Lone province code
            if tok.upper() in _PROVINCES:
                return tok, None, tok.upper()
        return None, None, None

    def _parse_flags(self, item: list) -> tuple[int, int]:
        """Return (is_lmia, is_direct_apply)."""
        joined = " ".join(str(x) for x in item).lower()
        is_lmia         = 1 if "lmia" in joined else 0
        is_direct_apply = 1 if "apply directly" in joined or "direct apply" in joined else 0
        return is_lmia, is_direct_apply

    def _parse_title_and_company(self, item: list, url: str | None) -> tuple[str | None, str | None]:
        """
        Title and company on Job Bank rows are plain text tokens.
        Heuristic: company names tend to be shorter and appear after the title.
        We skip tokens already consumed as pay/date/location/url.
        """
        candidates = []
        for tok in item:
            if not isinstance(tok, str):
                continue
            tok = tok.strip()
            if not tok:
                continue
            if _URL_PAT.search(tok) or _FULL_URL.search(tok):
                continue
            if _PAY_PAT.search(tok):
                continue
            if _DATE_PAT.search(tok):
                continue
            # Skip pure province codes
            if tok.upper() in _PROVINCES:
                continue
            # Skip tokens that look like "City, AB"
            if re.match(r'^.+,\s*[A-Z]{2}$', tok):
                continue
            # Skip LMIA / apply badges
            if re.search(r'lmia|apply directly|direct apply|job bank|jobbank', tok, re.IGNORECASE):
                continue
            candidates.append(tok)

        if not candidates:
            return None, None
        if len(candidates) == 1:
            return candidates[0], None

        # Title is usually the longest; company is typically shorter
        by_len  = sorted(candidates, key=len, reverse=True)
        title   = by_len[0]
        company = by_len[1] if len(by_len) > 1 else None
        return title, company

    # ── main API ───────────────────────────────────────────────────────────────

    def to_json(self, data: Any) -> List[dict]:
        self.processed_count = 0
        self.skipped_count   = 0
        self.skipped_data    = []
        self.success_data    = []

        if not data or not isinstance(data, list):
            return []

        for item in data:
            if not isinstance(item, list):
                self.skipped_count += 1
                self.skipped_data.append({"reason": "Not a list", "raw": str(item)})
                continue

            url, job_id = self._extract_url_and_id(item)
            if not url:
                self.skipped_count += 1
                self.skipped_data.append({"reason": "No job URL found", "raw": item})
                continue

            pay = self._parse_pay(item)
            if pay is None:
                self.skipped_count += 1
                self.skipped_data.append({"reason": "No hourly pay found", "raw": item})
                continue

            title, company            = self._parse_title_and_company(item, url)
            location_raw, city, prov  = self._parse_location(item)
            is_lmia, is_direct_apply  = self._parse_flags(item)

            if not title or len(title.strip()) < 3:
                self.skipped_count += 1
                self.skipped_data.append({"reason": "Title too short/missing", "raw": item})
                continue

            record = {
                "id":             job_id,
                "title":          title,
                "company":        company,
                "location_raw":   location_raw,
                "posted_date":    self._parse_date(item),
                "pay":            pay,
                "is_lmia":        is_lmia,
                "is_direct_apply": is_direct_apply,
                "url":            url,
                "city":           city,
                "state":          prov,
                "country":        "Canada",
            }
            self.success_data.append({k: record.get(k) for k in SCHEMA.field_names()})
            self.processed_count += 1

        return self.success_data

    def run_analysis(
        self,
        data: Any,
        print_samples: bool = False,
    ) -> List[dict]:
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


if __name__ == "__main__":
    # Run against demo data if available
    try:
        from _canadian_jobbank.demo_data import DEMO_DATA
    except ModuleNotFoundError:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
        from _canadian_jobbank.demo_data import DEMO_DATA

    j = CanadianJobbankJsonify(debug=True)
    results = j.run_analysis(DEMO_DATA, print_samples=True)
    print(f"\n{CY}Total records returned: {len(results)}{RESET}")
