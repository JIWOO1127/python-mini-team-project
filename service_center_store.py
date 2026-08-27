"""공식 제조사 페이지를 로컬 CSV로 동기화하고 즉시 검색한다."""

from __future__ import annotations

import csv
import json
import re
import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CATALOG_PATH = BASE_DIR / "service_centers.csv"
REFRESH_INTERVAL = 24 * 60 * 60
FIELDS = [
    "brand", "name", "address", "phone", "link",
    "latitude", "longitude", "source", "updated_at",
]

NISSAN_URL = "https://www.nissan.co.kr/dealer-finder.html"
VOLKSWAGEN_URL = "https://www.volkswagen.co.kr/app/locals/information/map/servicecenter.jsp"
TESLA_URL = "https://www.tesla.com/ko_KR/findus/list/services/South%2BKorea"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

# Tesla는 일반 HTTP 요청을 차단할 수 있어 공식 목록의 현재 스냅샷을 기본값으로 둔다.
TESLA_SEED = [
    ("Tesla 분당 서비스(고전압 불가)", "경기도 성남시 대왕판교로 316 13550"),
    ("Tesla 강서 서비스", "서울특별시 강서구 양천로66길 5 07553"),
    ("Tesla 노원 서비스(고전압 불가)", "서울특별시 노원구 수락산로 218-2 01616"),
    ("Tesla 광주 서비스", "광주광역시 서문대로517번길 13 61739"),
    ("Tesla 대구 서비스", "대구광역시 동대구로 50 42185"),
    ("Tesla 동탄 서비스", "경기도 화성시 경기동로 348 18510"),
    ("Tesla 문정 서비스", "서울특별시 송파구 동남로4길 36-1 05806"),
    ("Tesla 부산 서비스", "부산광역시 좌수영로 290 47568"),
    ("Tesla 성수 서비스", "서울특별시 성동구 광나루로8길 6 04799"),
    ("Tesla 세종 서비스", "세종특별자치시 종합운동장로 19 30154"),
    ("Tesla 용인 서비스", "경기도 용인시 중부대로 14 16978"),
    ("Tesla 원주 서비스(고전압 불가)", "강원특별자치도 원주시 지정면 신평리 1114-2"),
    ("Tesla 인천 서비스", "인천광역시 남동구 앵고개로 673 21677"),
    ("Tesla 일산 서비스", "경기도 고양시 덕이로 205 10212"),
    ("Tesla 제주 서비스", "제주특별자치도 제주시 애월읍 중산간서로 6432 63058"),
    ("Tesla 창원 서비스(고전압 불가)", "경상남도 창원시 의창구 차상로 56 51402"),
]

NISSAN_REGIONS = {
    "광주": "광주광역시",
    "대구": "대구광역시",
    "대전": "대전광역시",
    "부산": "부산광역시",
    "성수": "서울특별시 성동구",
    "안양": "경기도 안양시",
    "원주": "강원특별자치도 원주시",
    "인천": "인천광역시",
    "일산": "경기도 고양시 일산",
    "전주": "전북특별자치도 전주시",
    "제주": "제주특별자치도 제주시",
}


def _row(brand, name, address, phone, link, source, latitude="", longitude=""):
    return {
        "brand": brand,
        "name": " ".join(str(name).split()),
        "address": " ".join(str(address).split()),
        "phone": phone or "정보 없음",
        "link": link,
        "latitude": latitude,
        "longitude": longitude,
        "source": source,
        "updated_at": str(int(time.time())),
    }


def tesla_seed_rows():
    return [
        _row("Tesla", name, address, "080-617-1399", TESLA_URL, "Tesla 공식 센터 목록")
        for name, address in TESLA_SEED
    ]


def scrape_nissan(session) -> list[dict]:
    response = session.get(NISSAN_URL, headers=HEADERS, timeout=15)
    response.raise_for_status()
    response.encoding = "utf-8"
    match = re.search(
        r"HELIOS\.components\.c040\.dealers\s*=\s*(\{.*?\});",
        response.text,
        re.DOTALL,
    )
    if not match:
        raise RuntimeError("Nissan 센터 JSON을 찾지 못했습니다.")
    dealers = json.loads(match.group(1)).get("dealers", [])
    rows = []
    for dealer in dealers:
        geo = dealer.get("geolocation") or {}
        name = dealer.get("tradingName") or dealer.get("suggestedName", "Nissan 서비스센터")
        center_region = next(
            (address for keyword, address in NISSAN_REGIONS.items() if keyword in name),
            name.split(" 서비스")[0],
        )
        rows.append(_row(
            "Nissan",
            name,
            # 공식 JSON은 좌표와 지역명이 포함된 센터명을 제공한다.
            center_region,
            "정보 없음",
            NISSAN_URL,
            "Nissan 공식 딜러 목록",
            geo.get("latitude", ""),
            geo.get("longitude", ""),
        ))
    return rows


def scrape_volkswagen(session) -> list[dict]:
    from bs4 import BeautifulSoup

    response = session.get(VOLKSWAGEN_URL, headers=HEADERS, timeout=20)
    response.raise_for_status()
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    rows = []
    for item in soup.select(".accordion-item"):
        name_tag = item.select_one("strong.spot")
        address_tag = item.select_one("span.address")
        if not name_tag or not address_tag:
            continue
        phone = "정보 없음"
        for detail in item.select("div.item"):
            text = " ".join(detail.get_text(" ", strip=True).split())
            if "전화번호" in text:
                found = re.search(r"(?:0\d{1,2}-\d{3,4}-\d{4}|1\d{3}-\d{4})", text)
                if found:
                    phone = found.group()
                    break
        rows.append(_row(
            "Volkswagen",
            f"폭스바겐 {name_tag.get_text(strip=True)} 서비스센터",
            address_tag.get_text(" ", strip=True),
            phone,
            VOLKSWAGEN_URL,
            "Volkswagen Korea 공식 서비스센터",
        ))
    if not rows:
        raise RuntimeError("Volkswagen 센터 목록을 찾지 못했습니다.")
    return rows


def load_catalog() -> list[dict]:
    if not CATALOG_PATH.exists():
        return []
    with CATALOG_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def save_catalog(rows: list[dict]) -> None:
    unique = {}
    for row in rows:
        key = (row.get("brand", ""), row.get("name", ""), row.get("address", ""))
        unique[key] = {field: row.get(field, "") for field in FIELDS}
    ordered = sorted(unique.values(), key=lambda row: (row["brand"], row["address"], row["name"]))
    with CATALOG_PATH.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(ordered)


def refresh_catalog() -> dict[str, int]:
    """정적 공식 페이지를 갱신한다. 실패한 제조사는 기존 목록을 보존한다."""
    import requests

    existing = load_catalog()
    by_brand = {
        brand: [row for row in existing if row.get("brand") == brand]
        for brand in ("Nissan", "Volkswagen", "Tesla")
    }
    session = requests.Session()
    errors = []
    for brand, scraper in (("Nissan", scrape_nissan), ("Volkswagen", scrape_volkswagen)):
        try:
            fresh = scraper(session)
            if fresh:
                by_brand[brand] = fresh
        except Exception as exc:
            errors.append(f"{brand}: {exc}")
    # Tesla 요청은 403일 수 있으므로 안정적인 공식 스냅샷을 유지한다.
    if not by_brand["Tesla"]:
        by_brand["Tesla"] = tesla_seed_rows()
    save_catalog(by_brand["Nissan"] + by_brand["Volkswagen"] + by_brand["Tesla"])
    counts = {brand: len(rows) for brand, rows in by_brand.items()}
    if errors:
        counts["errors"] = len(errors)
    return counts


def ensure_catalog() -> None:
    if not CATALOG_PATH.exists():
        save_catalog(tesla_seed_rows())


def catalog_is_stale() -> bool:
    return not CATALOG_PATH.exists() or time.time() - CATALOG_PATH.stat().st_mtime > REFRESH_INTERVAL


def refresh_if_stale() -> None:
    was_missing = not CATALOG_PATH.exists()
    ensure_catalog()
    if was_missing or catalog_is_stale():
        refresh_catalog()


REGION_ALIASES = {
    "서울": "서울", "서울특별시": "서울",
    "경기": "경기", "경기도": "경기",
    "인천": "인천", "인천광역시": "인천",
    "부산": "부산", "부산광역시": "부산",
    "대구": "대구", "대구광역시": "대구",
    "광주": "광주", "광주광역시": "광주",
    "대전": "대전", "대전광역시": "대전",
    "세종": "세종", "세종특별자치시": "세종",
    "강원": "강원", "강원도": "강원", "강원특별자치도": "강원",
    "충북": "충북", "충청북도": "충북", "충남": "충남", "충청남도": "충남",
    "전북": "전북", "전북특별자치도": "전북", "전남": "전남", "전라남도": "전남",
    "경북": "경북", "경상북도": "경북", "경남": "경남", "경상남도": "경남",
    "제주": "제주", "제주특별자치도": "제주",
}

REGION_NEIGHBORS = {
    "서울": ["경기", "인천"],
    "경기": ["서울", "인천", "충남", "충북", "강원"],
    "인천": ["경기", "서울"],
    "강원": ["경기", "충북", "경북"],
    "충북": ["세종", "대전", "충남", "경기", "강원", "경북"],
    "충남": ["세종", "대전", "경기", "충북", "전북"],
    "대전": ["세종", "충남", "충북"],
    "세종": ["대전", "충남", "충북"],
    "전북": ["대전", "충남", "광주", "전남", "경북"],
    "전남": ["광주", "전북", "경남", "제주"],
    "광주": ["전남", "전북"],
    "경북": ["대구", "울산", "경남", "충북", "강원", "전북"],
    "대구": ["경북", "경남"],
    "경남": ["부산", "울산", "대구", "경북", "전남"],
    "부산": ["경남", "울산"],
    "울산": ["경남", "부산", "경북"],
    "제주": ["전남"],
}


def _tokens(location: str) -> list[str]:
    parts = re.findall(r"[가-힣A-Za-z0-9]+", _normalize_location(location))
    return [REGION_ALIASES.get(part, part) for part in parts if len(part) >= 2]


def _normalize_location(text: str) -> str:
    """서울시/서울특별시, 강남/강남구 같은 행정구역 표현을 통일한다."""
    normalized = str(text)
    for suffix in ("특별자치도", "특별자치시", "특별시", "광역시"):
        normalized = normalized.replace(suffix, " ")
    normalized = re.sub(r"(?<=[가-힣])(도|시|군|구)(?=\s|$)", "", normalized)
    return " ".join(normalized.split())


def _province(text: str) -> str:
    """주소에서 광역 시·도 이름을 찾는다."""
    source = str(text)
    # 긴 공식 명칭을 먼저 검사해 경기도 광주시 같은 주소를 경기로 판정한다.
    for official, alias in sorted(REGION_ALIASES.items(), key=lambda item: -len(item[0])):
        if official in source:
            return alias
    normalized = _normalize_location(source)
    first = normalized.split()[0] if normalized.split() else ""
    return REGION_ALIASES.get(first, first if first in REGION_NEIGHBORS else "")


def _fallback_rows(rows: list[dict], location: str, limit: int) -> list[dict]:
    requested_region = _province(location)
    if not requested_region:
        return []

    def rows_in(region: str) -> list[dict]:
        found = [row for row in rows if _province(row.get("address", "")) == region]
        return found[:limit]

    # 같은 시·도에서 다른 시·군·구를 가장 먼저 추천한다.
    candidates = rows_in(requested_region)
    fallback_region = requested_region
    if not candidates:
        for neighbor in REGION_NEIGHBORS.get(requested_region, []):
            candidates = rows_in(neighbor)
            if candidates:
                fallback_region = neighbor
                break

    results = []
    for row in candidates:
        recommended = dict(row)
        recommended["fallback"] = "1"
        recommended["fallback_region"] = fallback_region
        results.append(recommended)
    return results


def search_centers(location: str, brand: str, limit: int = 20) -> list[dict]:
    """로컬 CSV만 검색한다. 네트워크나 브라우저를 사용하지 않는다."""
    ensure_catalog()
    rows = [row for row in load_catalog() if row.get("brand") == brand]
    tokens = list(dict.fromkeys(_tokens(location)))
    if not tokens:
        return []
    ranked = []
    for index, row in enumerate(rows):
        haystack = _normalize_location(f"{row.get('name', '')} {row.get('address', '')}")
        normalized = haystack
        for original, alias in REGION_ALIASES.items():
            normalized = normalized.replace(original, alias)
        score = sum(1 for token in tokens if token in normalized)
        ranked.append((score, index, row))
    # 입력된 시/도와 시/군/구 조건이 모두 맞는 센터만 보여준다.
    matching = [item for item in ranked if item[0] == len(tokens)]
    matching.sort(key=lambda item: (-item[0], item[1]))
    if matching:
        return [row for _, _, row in matching[:limit]]
    return _fallback_rows(rows, location, limit)


if __name__ == "__main__":
    print(refresh_catalog())
