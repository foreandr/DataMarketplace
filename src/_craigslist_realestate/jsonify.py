"""Jsonify for _craigslist_realestate."""
from __future__ import annotations

from typing import Any, List
from datetime import datetime, timedelta
from pathlib import Path
import re

try:
    from _craigslist_realestate.schema import SCHEMA
except ModuleNotFoundError:
    import sys
    from pathlib import Path
    ROOT_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT_DIR / "src"))
    from _craigslist_realestate.schema import SCHEMA


class CraigslistRealestateJsonify:
    def __init__(self, source_name: str = "_craigslist_realestate"):
        self.source_name = source_name
        self.processed_count = 0
        self.skipped_count = 0
        self.skipped_data = []
        self.success_data = []
        self._skip_log_path = Path(__file__).resolve().parents[0] / "skipped_listings.txt"

    def _parse_price(self, item: list) -> int | None:
        for x in item:
            if isinstance(x, str) and "$" in x:
                digits = re.sub(r"[^\d]", "", x)
                if digits:
                    return int(digits)
        return None

    def _parse_bedrooms(self, item: list) -> int | None:
        for x in item:
            if not isinstance(x, str):
                continue
            m = re.search(r"(\d+)\s*br", x.lower())
            if m:
                return int(m.group(1))
            if "studio" in x.lower():
                return 0
        return None

    def _parse_sqft(self, item: list) -> int | None:
        for x in item:
            if not isinstance(x, str):
                continue
            m = re.search(r"(\d{2,5})\s*(?:ft|ft2|sqft|sq\.?ft)", x.lower())
            if m:
                return int(m.group(1))
        return None

    def _parse_bathrooms(self, item: list) -> float | None:
        # Try explicit "bath" tokens first
        for x in item:
            if not isinstance(x, str):
                continue
            m = re.search(r"(\d+(?:\.\d+)?)\s*(?:ba|bath|baths?)", x.lower())
            if m:
                return float(m.group(1))

        # Fallback: a lone numeric token between sqft and price
        price_idx = next((i for i, v in enumerate(item) if isinstance(v, str) and "$" in v), None)
        if price_idx is None:
            return None
        sqft_idx = next(
            (i for i, v in enumerate(item)
             if isinstance(v, str) and re.search(r"\d{2,5}\s*(?:ft|ft2|sqft|sq\.?ft)", v.lower())),
            None,
        )
        if sqft_idx is None:
            return None
        for i in range(sqft_idx + 1, price_idx):
            v = item[i]
            if isinstance(v, str) and re.fullmatch(r"\d+(?:\.\d+)?", v.strip()):
                try:
                    return float(v)
                except ValueError:
                    return None
        return None

    def _parse_posted_date(self, date_str: str) -> str:
        now = datetime.now()
        ds = str(date_str).lower().strip()
        try:
            if "ago" in ds:
                m = re.search(r"(\d+)", ds)
                if not m:
                    return now.strftime("%Y-%m-%d %H:%M:%S")
                amount = int(m.group(1))
                if "h" in ds:
                    dt = now - timedelta(hours=amount)
                else:
                    dt = now - timedelta(minutes=amount)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            if "/" in ds:
                dt = datetime.strptime(f"{ds}/{now.year}", "%m/%d/%Y")
                return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
        return now.strftime("%Y-%m-%d %H:%M:%S")

    def _detect_housing_type(self, title: str) -> str | None:
        t = (title or "").lower()
        patterns = [
            (r"\bapartment\b", "apartment"),
            (r"\bapt\b|\bapts\b", "apartment"),
            (r"\bcondo\b|\bcondominium\b", "condo"),
            (r"\bhouse\b|\bhome\b", "house"),
            (r"\bduplex\b", "duplex"),
            (r"\btriplex\b", "triplex"),
            (r"\btownhouse\b|\btownhome\b|\btown house\b", "townhouse"),
            (r"\bstudio\b", "studio"),
            (r"\bloft\b", "loft"),
            (r"\bbasement\b", "basement"),
            (r"\broom\b", "room"),
            (r"\bshared\b|\bshare\b", "shared"),
        ]
        for pattern, label in patterns:
            if re.search(pattern, t):
                return label
        return None

    def to_json(self, data: Any, location: dict | None = None) -> List[dict]:
        self.processed_count = 0
        self.skipped_count = 0
        self.skipped_data = []
        self.success_data = []

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

            url = next((x for x in item if isinstance(x, str) and "craigslist.org" in x and "/d/" in x), None)
            title = str(item[1]) if len(item) > 1 else ""
            location_str = str(item[2]) if len(item) > 2 else None
            posted_date = str(item[4]) if len(item) > 4 else None
            image_url = next((x for x in item if isinstance(x, str) and "craigslist.org/images" in x), None)
            price = self._parse_price(item)
            bedrooms = self._parse_bedrooms(item)
            bathrooms = self._parse_bathrooms(item)
            sqft = self._parse_sqft(item)

            # ---- Filters for likely fake/low-quality listings ----
            reason = None
            if price is None:
                reason = "Missing price"
            elif price < 300:
                reason = f"Price too low (${price})"
            elif url is None:
                reason = "Missing URL"
            elif len(title.strip()) < 10:
                reason = "Title too short"
            elif "wanted" in title.lower():
                reason = "Wanted ad (not a listing)"
            elif bedrooms is not None and bedrooms > 12:
                reason = f"Unrealistic bedrooms ({bedrooms})"
            elif bathrooms is not None and (bathrooms <= 0 or bathrooms > 10):
                reason = f"Unrealistic bathrooms ({bathrooms})"
            elif sqft is not None and (sqft < 100 or sqft > 20000):
                reason = f"Unrealistic sqft ({sqft})"

            if reason:
                self.skipped_count += 1
                self.skipped_data.append({"reason": reason, "raw": item, "url": url, "title": title})
                continue

            record = {
                "id": str(item[0]) if len(item) > 0 else None,
                "title": title,
                "price": price,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "square_feet": sqft,
                "housing_type": self._detect_housing_type(title),
                "location": location_str,
                "posted_date": self._parse_posted_date(posted_date),
                "url": url,
                "image_url": image_url,
                "city": loc_city,
                "state": loc_state,
                "country": loc_country,
            }
            self.success_data.append({k: record.get(k) for k in SCHEMA.field_names()})
            self.processed_count += 1

        self._write_skip_log()
        return self.success_data

    def run_analysis(
        self,
        data: Any,
        location: dict | None = None,
        print_samples: bool = False,
    ) -> List[dict]:
        # Placeholder to match crawler API (now returns parsed results).
        _ = print_samples  # unused for now
        return self.to_json(data, location=location)

    def _write_skip_log(self) -> None:
        if not self.skipped_data:
            return
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._skip_log_path.open("a", encoding="utf-8") as f:
            f.write(f"\n=== SKIPPED @ {ts} ===\n")
            for item in self.skipped_data:
                reason = item.get("reason", "Unknown")
                title = item.get("title", "")
                url = item.get("url", "")
                raw = item.get("raw", "")
                f.write(
                    f"- {reason}\n"
                    f"  title: {title}\n"
                    f"  url: {url}\n"
                    f"  raw: {str(raw)[:500]}\n\n"
                )
