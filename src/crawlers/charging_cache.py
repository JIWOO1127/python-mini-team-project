"""Short-lived CSV cache for charging-station search results."""

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_FILE = PROJECT_ROOT / "data" / "processed" / "charging_station_cache.csv"
CACHE_TTL = timedelta(minutes=10)
CACHE_COLUMNS = [
    "search_location", "name", "address", "available",
    "slow_available", "fast_available", "detail_url", "cached_at",
]


def _normalized_location(location):
    return " ".join(location.strip().casefold().split())


def _optional_int(value):
    return None if value in (None, "") else int(value)


def load_charging_cache(location, now=None):
    if not CACHE_FILE.exists():
        return []

    now = now or datetime.now(timezone.utc)
    key = _normalized_location(location)
    results = []
    with CACHE_FILE.open("r", newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            if row["search_location"] != key:
                continue
            cached_at = datetime.fromisoformat(row["cached_at"])
            if now - cached_at > CACHE_TTL:
                return []
            results.append({
                "name": row["name"],
                "address": row["address"],
                "available": _optional_int(row["available"]),
                "slow_available": _optional_int(row["slow_available"]),
                "fast_available": _optional_int(row["fast_available"]),
                "detail_url": row["detail_url"] or None,
            })
    return results


def save_charging_cache(location, stations, now=None):
    if not stations:
        return

    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    now = now or datetime.now(timezone.utc)
    key = _normalized_location(location)
    retained = []
    if CACHE_FILE.exists():
        with CACHE_FILE.open("r", newline="", encoding="utf-8-sig") as file:
            retained = [
                row for row in csv.DictReader(file)
                if row["search_location"] != key
            ]

    with CACHE_FILE.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=CACHE_COLUMNS)
        writer.writeheader()
        writer.writerows(retained)
        for station in stations:
            writer.writerow({
                "search_location": key,
                "name": station.get("name", ""),
                "address": station.get("address", ""),
                "available": station.get("available"),
                "slow_available": station.get("slow_available"),
                "fast_available": station.get("fast_available"),
                "detail_url": station.get("detail_url") or "",
                "cached_at": now.isoformat(),
            })


def cached_station_search(location, search):
    cached = load_charging_cache(location)
    if cached:
        return cached
    stations = search(location)
    save_charging_cache(location, stations)
    return stations
