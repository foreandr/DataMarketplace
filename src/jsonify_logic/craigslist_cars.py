from __future__ import annotations
from typing import Any, List
from datetime import datetime, timedelta
import re

try:
    from jsonify_logic.base import Jsonify
except ModuleNotFoundError:
    import sys
    from pathlib import Path
    ROOT_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT_DIR / "src"))
    from jsonify_logic.base import Jsonify

class CraigslistCarsJsonify(Jsonify):
    def _parse_price(self, item: list) -> int | None:
        # Find the string containing '$'
        price_str = next((x for x in item if isinstance(x, str) and "$" in x), None)
        if not price_str:
            return None
        # Extract digits only: "$13,999" -> 13999
        digits = re.sub(r'[^\d]', '', price_str)
        return int(digits) if digits else None

    def _parse_mileage(self, item: list) -> int | None:
        # Look for the string containing 'mi'
        mi_str = next((x for x in item if isinstance(x, str) and "mi" in x.lower()), None)
        if not mi_str:
            return None
        # Handle 'k' multiplier: "85k mi" -> 85000
        val = mi_str.lower().replace('mi', '').strip()
        multiplier = 1
        if 'k' in val:
            multiplier = 1000
            val = val.replace('k', '')
        
        digits = re.sub(r'[^\d.]', '', val)
        try:
            return int(float(digits) * multiplier)
        except ValueError:
            return None

    def _parse_date(self, date_str: str) -> str | None:
        now = datetime.now()
        date_str = date_str.lower().strip()
        
        try:
            # Handle "Xh ago" or "Xm ago"
            if "ago" in date_str:
                amount = int(re.search(r'\d+', date_str).group())
                if "h" in date_str:
                    dt = now - timedelta(hours=amount)
                elif "m" in date_str:
                    dt = now - timedelta(minutes=amount)
                else:
                    dt = now
            # Handle "3/8" or "3/9" (Assumes current year 2026)
            elif "/" in date_str:
                dt = datetime.strptime(f"{date_str}/2026", "%m/%d/%Y")
            else:
                return None
            
            return dt.isoformat()
        except Exception:
            return None

    def to_json(self, data: Any) -> List[dict]:
        if not isinstance(data, list):
            return []

        jsonified_results = []
        
        for item in data:
            if not isinstance(item, list):
                continue

            # 1. PRICE VALIDATION (Essential)
            price = self._parse_price(item)
            if price is None:
                continue # Skip if no valid price found

            # 2. URL/IMAGE VALIDATION
            url = next((x for x in item if "craigslist.org" in str(x) and "/d/" in str(x)), None)
            image_url = next((x for x in item if any(ext in str(x) for ext in [".png", ".jpg", ".jpeg"])), None)
            
            if not url: # Skip if no direct link to the ad
                continue

            # 3. DATE PARSING
            raw_time = item[4] if len(item) > 4 else ""
            posted_date = self._parse_date(raw_time)

            # 4. BUILDING THE RECORD
            record = {
                "id": item[0] if len(item) > 0 else None,
                "title": item[1] if len(item) > 1 else "Unknown",
                "region": item[3] if len(item) > 3 else "N/A",
                "posted_at": posted_date,
                "mileage": self._parse_mileage(item),
                "price": price,
                "url": url,
                "image_url": image_url
            }
            
            # Final Check: If the price ended up being the title (like in your rogue example)
            # or if region looks like a generic ad string, we could add more filters here.
            if len(record["region"]) > 30: # Likely "GET PRE APPROVED..." garbage
                record["region"] = "Unknown"

            jsonified_results.append(record)

        return jsonified_results

    def demo_data(self) -> Any:
        from demo_data.craigslist_cars import DEMO_DATA
        return DEMO_DATA

if __name__ == "__main__":
    jsonifier = CraigslistCarsJsonify("craigslist_cars")
    sample = jsonifier.demo_data()
    result = jsonifier.to_json(sample)
    
    import json
    print(json.dumps(result, indent=2))