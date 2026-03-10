"""Geography helpers."""
from __future__ import annotations

from typing import List

from db.cities_can import cities_can
from db.cities_us import cities_us
import random

def _extract_city_names(rows: List[dict]) -> List[str]:
    names: List[str] = []
    for row in rows:
        name = row.get("city", "").strip()
        if name:
            names.append(name)
    return names


def get_cities_can() -> List[str]:
    return _extract_city_names(cities_can)


def get_cities_us() -> List[str]:
    return _extract_city_names(cities_us)


def get_all_cities() -> List[str]:
    all_cities = get_cities_us() + get_cities_can()
    # random.sample(list, len(list)) returns a new shuffled list
    return random.sample(all_cities, k=len(all_cities))
