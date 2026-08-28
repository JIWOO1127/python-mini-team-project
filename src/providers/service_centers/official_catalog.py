from __future__ import annotations

import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from src.providers.geocoding.kakao import ProviderError


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CACHE_FILE = PROJECT_ROOT / "data" / "cache" / "service_centers.csv"
TTL_SECONDS = 24 * 60 * 60
BRANDS = ("Tesla", "Nissan", "Volkswagen")
FIELDS = ["brand", "name", "address", "phone", "detail_url", "latitude", "longitude", "source", "fetched_at"]
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept-Language": "ko-KR,ko;q=0.9"}

TESLA_SEED = [
    ("Tesla 강서 서비스", "서울특별시 강서구 양천로66길 5"),
    ("Tesla 성수 서비스", "서울특별시 성동구 광나루로8길 6"),
    ("Tesla 분당 서비스", "경기도 성남시 대왕판교로 316"),
    ("Tesla 동탄 서비스", "경기도 화성시 경기동로 348"),
    ("Tesla 대구 서비스", "대구광역시 동대구로 50"),
    ("Tesla 부산 서비스", "부산광역시 좌수영로 290"),
]

NISSAN_SEED = [
    ("닛산 성수 서비스", "서울특별시 성동구 왕십리로 130", "02-460-9999"),
    ("닛산 일산 서비스", "경기도 고양시 일산동구 백마로 522", "031-810-1501"),
    ("닛산 신갈 서비스", "경기도 용인시 기흥구 용구대로 1845", "031-810-1501"),
    ("닛산 인천 서비스", "인천광역시 부평구 열우물로 159", "032-574-0638"),
    ("닛산 안양 서비스", "경기도 안양시 만안구 만안로 100", "031-443-7777"),
    ("닛산 대전 서비스", "대전광역시 동구 동서대로 1734", "042-670-0010"),
    ("닛산 전주 서비스", "전주시 완산구 쑥고개로 372", "063-270-0010"),
    ("닛산 광주 서비스", "광주광역시 북구 하서로 672번길 8", "062-515-1112"),
    ("닛산 대구 서비스", "대구시 서구 서대구로 63안길 13", "053-341-2700"),
    ("닛산 부산 서비스", "부산시 남구 신선로 420", "051-610-7555"),
    ("닛산 제주 서비스", "제주특별자치도 제주시 선반남길2길 63", "064-756-9402"),
]


def _row(brand: str, name: str, address: str, phone: str, detail_url: str, source: str, latitude=None, longitude=None) -> dict:
    return {
        "brand": brand, "name": " ".join(name.split()), "address": " ".join(address.split()),
        "phone": phone or "정보 없음", "detail_url": detail_url, "latitude": latitude or "",
        "longitude": longitude or "", "source": source, "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


class OfficialServiceCenterProvider:
    name = "official-manufacturer-catalog"

    def _read(self) -> list[dict]:
        if not CACHE_FILE.exists():
            return []
        with CACHE_FILE.open(encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))

    def _write(self, rows: list[dict]) -> None:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        unique = {(row["brand"], row["name"], row["address"]): row for row in rows}
        with CACHE_FILE.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(sorted(unique.values(), key=lambda row: (row["brand"], row["address"], row["name"])))

    def _is_stale(self) -> bool:
        return not CACHE_FILE.exists() or time.time() - CACHE_FILE.stat().st_mtime > TTL_SECONDS

    def _nissan(self, session: requests.Session) -> list[dict]:
        url = "https://www.nissan.co.kr/dealer-finder.html"
        response = session.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        match = re.search(r"HELIOS\.components\.c040\.dealers\s*=\s*(\{.*?\});", response.text, re.DOTALL)
        if not match:
            return []
        dealers = json.loads(match.group(1)).get("dealers", [])
        rows = []
        for dealer in dealers:
            geo = dealer.get("geolocation") or {}
            name = dealer.get("tradingName") or dealer.get("suggestedName") or "Nissan 서비스센터"
            address = dealer.get("address") or name.split(" 서비스")[0]
            rows.append(_row("Nissan", name, address, "정보 없음", url, "Nissan 공식 딜러 목록", geo.get("latitude"), geo.get("longitude")))
        return rows

    @staticmethod
    def _nissan_fallback() -> list[dict]:
        url = "https://www.nissan.co.kr/dealer-finder.html"
        return [_row("Nissan", name, address, phone, url, "Nissan 공식 목록 스냅샷") for name, address, phone in NISSAN_SEED]

    def _volkswagen(self, session: requests.Session) -> list[dict]:
        url = "https://www.volkswagen.co.kr/app/locals/information/map/servicecenter.jsp"
        response = session.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        rows = []
        for item in soup.select(".accordion-item"):
            name, address = item.select_one("strong.spot"), item.select_one("span.address")
            if not name or not address:
                continue
            phone_match = re.search(r"(?:0\\d{1,2}-\\d{3,4}-\\d{4}|1\\d{3}-\\d{4})", item.get_text(" ", strip=True))
            rows.append(_row("Volkswagen", f"폭스바겐 {name.get_text(strip=True)} 서비스센터", address.get_text(" ", strip=True), phone_match.group() if phone_match else "정보 없음", url, "Volkswagen 공식 서비스센터"))
        return rows

    @staticmethod
    def _kakao_fallback(address: str, brand: str, limit: int) -> list[dict]:
        """Use the repository's Selenium crawler when an official page is empty.

        The crawler is deliberately a search-time fallback: it needs the user's
        address, whereas the official catalog is a nationwide refresh cache.
        """
        try:
            from src.crawlers.crawler2 import search_service_centers
            results = search_service_centers(address, brand, limit)
        except Exception:
            return []
        return [
            _row(brand, item.get("name", f"{brand} 서비스센터"), item.get("address", "주소 정보 없음"),
                 item.get("phone", "정보 없음"), item.get("link", ""), "KakaoMap 서비스센터 크롤러")
            for item in results
        ]

    def refresh(self) -> list[dict]:
        existing = self._read()
        by_brand = {brand: [row for row in existing if row.get("brand") == brand] for brand in BRANDS}
        session = requests.Session()
        for brand, collector in (("Nissan", self._nissan), ("Volkswagen", self._volkswagen)):
            try:
                fresh = collector(session)
                if fresh:
                    by_brand[brand] = fresh
            except requests.RequestException:
                if brand == "Nissan" and not by_brand[brand]:
                    by_brand[brand] = self._nissan_fallback()
        if not by_brand["Nissan"]:
            by_brand["Nissan"] = self._nissan_fallback()
        if not by_brand["Tesla"]:
            by_brand["Tesla"] = [_row("Tesla", name, address, "080-617-1399", "https://www.tesla.com/ko_kr/findus", "Tesla 공식 목록 스냅샷") for name, address in TESLA_SEED]
        rows = [row for brand in BRANDS for row in by_brand[brand]]
        self._write(rows)
        return rows

    @staticmethod
    def _tokens(address: str) -> list[str]:
        return [token for token in re.findall(r"[가-힣A-Za-z0-9]+", address) if len(token) >= 2]

    def search(self, address: str, brand: str, limit: int = 10) -> list[dict]:
        if brand not in BRANDS:
            raise ProviderError(f"지원하지 않는 제조사입니다: {brand}")
        rows = self.refresh() if self._is_stale() else self._read()
        tokens = self._tokens(address)
        selected = [row for row in rows if row.get("brand") == brand]
        # A cache created by an older failed crawl may be fresh but contain no
        # Nissan rows. Refresh once, then use the bundled official snapshot.
        if brand == "Nissan" and not selected:
            rows = self.refresh()
            selected = [row for row in rows if row.get("brand") == brand]
        if brand == "Nissan" and not selected:
            selected = self._nissan_fallback()
        if brand == "Volkswagen" and not selected:
            selected = self._kakao_fallback(address, brand, limit)
        ranked = sorted(selected, key=lambda row: sum(token in f"{row.get('name', '')} {row.get('address', '')}" for token in tokens), reverse=True)
        fetched_at = datetime.now(timezone.utc).isoformat()
        return [
            {
                "name": row["name"], "address": row["address"], "latitude": float(row["latitude"]) if row.get("latitude") else None,
                "longitude": float(row["longitude"]) if row.get("longitude") else None, "distance_km": None,
                "phone": row.get("phone", "정보 없음"), "available": None, "slow_available": None, "fast_available": None,
                "detail_url": row.get("detail_url"), "source": row.get("source", self.name), "fetched_at": row.get("fetched_at", fetched_at), "cached": not self._is_stale(),
            }
            for row in ranked[:limit]
        ]
