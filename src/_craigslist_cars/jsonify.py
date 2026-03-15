"""Jsonify for _craigslist_cars."""
from __future__ import annotations

from typing import Any, List
from datetime import datetime, timedelta
import re
import json
import random

try:
    from _craigslist_cars.schema import SCHEMA
except ModuleNotFoundError:
    import sys
    from pathlib import Path
    ROOT_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT_DIR / "src"))
    from _craigslist_cars.schema import SCHEMA

from _craigslist_cars.demo_data import DEMO_DATA
data_to_process = DEMO_DATA

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


class CraigslistCarsJsonify:
    def __init__(self, name: str = "_craigslist_cars", debug: bool = False):
        self.source_name = name
        self.processed_count = 0
        self.skipped_count = 0
        self.skipped_data = []
        self.success_data = []

    def _parse_price(self, item: list) -> int | None:
        for x in item:
            if isinstance(x, str) and "$" in x and len(x) < 25:
                digits = re.sub(r'[^\d]', '', x)
                if digits: return int(digits)
        return None

    def _parse_mileage(self, item: list) -> int | None:
        mi_str = next((x for x in item if isinstance(x, str) and ("mi" in x.lower() or "miles" in x.lower())), None)
        if not mi_str: return None
        val = re.sub(r'(?i)mi(les)?', '', mi_str).strip()
        multiplier = 1000 if 'k' in val.lower() else 1
        digits = re.sub(r'[^\d.]', '', val)
        try:
            miles = int(float(digits) * multiplier)
            if miles > 500_000:
                return None
            return miles
        except:
            return None

    def _parse_date(self, date_str: str) -> str | None:
        now = datetime.now()
        date_str = str(date_str).lower().strip()
        try:
            if "ago" in date_str:
                match = re.search(r'\d+', date_str)
                if not match: return now.strftime("%Y-%m-%d %H:%M:%S")
                amount = int(match.group())
                dt = now - (timedelta(hours=amount) if "h" in date_str else timedelta(minutes=amount))
            elif "/" in date_str:
                dt = datetime.strptime(f"{date_str}/2026", "%m/%d/%Y")
            else:
                return now.strftime("%Y-%m-%d %H:%M:%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return now.strftime("%Y-%m-%d %H:%M:%S")

    def _extract_year(self, title: str) -> int | None:
        match = re.search(r'\b(19\d{2}|20\d{2})\b', title)
        if match:
            year = int(match.group())
            if 1900 <= year <= 2027:
                return year
        return None

    def to_json(self, data: Any) -> List[dict]:
        self.processed_count = 0
        self.skipped_count = 0
        self.skipped_data = []
        self.success_data = []

        if not data or not isinstance(data, list):
            return []

        for item in data:
            reason = None
            if not isinstance(item, list):
                self.skipped_count += 1
                self.skipped_data.append({"reason": "Not a list", "raw": str(item)})
                continue

            price = self._parse_price(item)
            url = next((x for x in item if isinstance(x, str) and "craigslist.org" in x and ("/d/" in x or "/7" in x)), None)
            title = str(item[1]) if len(item) > 1 else ""
            year = self._extract_year(title)

            if price is None:
                reason = "Invalid/Missing Price"
            elif price < 750:
                reason = f"Price too low (${price})"
            elif year is None:
                reason = "No year found in title"
            elif url is None:
                reason = "Missing URL"

            if reason:
                self.skipped_count += 1
                self.skipped_data.append({"reason": reason, "raw": item})
                continue

            record = {
                "id": str(item[0]) if len(item) > 0 else None,
                "title": title,
                "year": year,
                "posted_at": self._parse_date(item[4] if len(item) > 4 else ""),
                "mileage": self._parse_mileage(item),
                "price": price,
                "url": url,
                "image_url": next((x for x in item if isinstance(x, str) and any(ext in x.lower() for ext in [".png", ".jpg", ".jpeg", "images"])), None)
            }
            self.success_data.append({k: record.get(k) for k in SCHEMA.field_names()})
            self.processed_count += 1

        return self.success_data

    def run_analysis(self, data: Any, print_samples: bool = False) -> List[dict]:
        results = self.to_json(data)
        if not print_samples:
            return results

        if self.success_data:
            num = min(8, len(self.success_data))
            print(f"\n{BOLD}--- SUCCESS DATA ({num} RANDOM SAMPLES) ---{RESET}")
            for rec in random.sample(self.success_data, num):
                print(f"{GREEN}{json.dumps(rec, indent=2)}{RESET}")

        if self.skipped_data:
            num_fail = min(8, len(self.skipped_data))
            print(f"\n{BOLD}--- FAILED DATA ({num_fail} RANDOM SAMPLES) ---{RESET}")
            for fail in random.sample(self.skipped_data, num_fail):
                print(f"{RED}REASON: {fail['reason']}{RESET}")
                print(f"{RED}DATA: {str(fail['raw'])[:320]}...{RESET}\n")

        total = self.processed_count + self.skipped_count
        rate = (self.processed_count / total * 100) if total > 0 else 0
        print(f"\n{BOLD}{'='*40}\nANALYSIS COMPLETE\nItems Processed: {GREEN}{self.processed_count}{RESET}\nItems Skipped:   {RED}{self.skipped_count}{RESET}\nSuccess Rate:    {BOLD}{rate:.1f}%{RESET}\n{'='*40}{RESET}")

        return results


if __name__ == "__main__":
    jsonifier = CraigslistCarsJsonify()
    result = jsonifier.to_json(data_to_process)
    print(f"Processed: {jsonifier.processed_count} | Skipped: {jsonifier.skipped_count}")
