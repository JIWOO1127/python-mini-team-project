"""카카오맵에서 브랜드 서비스센터를 검색합니다."""

import csv
import re
from pathlib import Path
from urllib.parse import quote

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


BRANDS = {
    "Nissan": "닛산 서비스센터",
    "Volkswagen": "폭스바겐 서비스센터",
    "Tesla": "테슬라 서비스센터",
}

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_FILE = PROJECT_ROOT / "data" / "processed" / "service_center_cache.csv"
CACHE_COLUMNS = [
    "search_region", "brand", "name", "address", "phone", "link",
]


def create_driver():
    """백그라운드 크롤링용 Chrome 드라이버를 생성합니다."""

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1300,900")
    options.add_argument("--lang=ko-KR")
    return webdriver.Chrome(options=options)


def extract_phone(text):
    patterns = [
        r"0\d{1,2}-\d{3,4}-\d{4}",
        r"080-\d{3,4}-\d{4}",
        r"1\d{3}-\d{4}",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group()
    return "정보 없음"


def extract_name(item):
    xpaths = [
        ".//a[contains(@class,'link_name')]",
        ".//strong/a",
        ".//strong",
    ]

    for xpath in xpaths:
        try:
            text = item.find_element(By.XPATH, xpath).text.strip()
            if text:
                return text
        except Exception:
            continue

    lines = [line.strip() for line in item.text.split("\n") if line.strip()]
    return lines[0] if lines else ""


def extract_address(item):
    xpaths = [
        ".//div[contains(@class,'addr')]//p[1]",
        ".//p[contains(@class,'addr')]",
        ".//*[contains(@class,'addr')]",
    ]

    for xpath in xpaths:
        try:
            for element in item.find_elements(By.XPATH, xpath):
                text = element.text.strip()
                if len(text) > 5:
                    return text.split("\n")[0]
        except Exception:
            continue

    regions = [
        "서울", "부산", "대구", "인천", "광주", "대전", "울산",
        "세종", "경기", "강원", "충북", "충남", "전북", "전남",
        "경북", "경남", "제주",
    ]
    for line in item.text.split("\n"):
        line = line.strip()
        if any(region in line for region in regions):
            return line
    return "주소 정보 없음"


def extract_link(item):
    try:
        for link in item.find_elements(By.TAG_NAME, "a"):
            href = link.get_attribute("href") or ""
            if "place.map.kakao.com" in href:
                return href
    except Exception:
        pass
    return ""


def is_service_center(brand, name, full_text):
    brand_words = {
        "Nissan": ["닛산", "nissan"],
        "Volkswagen": ["폭스바겐", "volkswagen"],
        "Tesla": ["테슬라", "tesla"],
    }
    service_words = ["서비스", "서비스센터", "정비", "service"]
    text = f"{name} {full_text}".lower()

    has_brand = any(word.lower() in text for word in brand_words[brand])
    has_service = any(word.lower() in text for word in service_words)
    return has_brand and has_service


def crawl_kakao(driver, region, brand, limit=5):
    """카카오맵 검색 결과에서 서비스센터 목록을 추출합니다."""

    query = f"{region} {BRANDS[brand]}"
    driver.get(f"https://map.kakao.com/?q={quote(query)}")

    try:
        WebDriverWait(driver, 6).until(
            lambda current_driver: current_driver.find_elements(
                By.XPATH,
                '//*[@id="info.search.place.list"]/li',
            )
        )
    except TimeoutException:
        return []

    items = driver.find_elements(
        By.XPATH,
        '//*[@id="info.search.place.list"]/li',
    )
    results = []

    for item in items:
        full_text = item.text.strip()
        name = extract_name(item)
        if not full_text or not name:
            continue
        if not is_service_center(brand, name, full_text):
            continue

        center = {
            "name": name,
            "address": extract_address(item),
            "phone": extract_phone(full_text),
            "link": extract_link(item),
            "brand": brand,
        }
        duplicate = any(
            old["name"] == center["name"]
            and old["address"] == center["address"]
            for old in results
        )
        if not duplicate:
            results.append(center)
        if len(results) >= limit:
            break

    return results


def get_broad_region(region):
    """'경북 경산시'를 '경북'처럼 넓은 지역명으로 변환합니다."""

    words = region.strip().split()
    return words[0] if len(words) >= 2 else region.strip()


def create_cache_file():
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not CACHE_FILE.exists():
        with CACHE_FILE.open("w", newline="", encoding="utf-8-sig") as file:
            csv.DictWriter(file, fieldnames=CACHE_COLUMNS).writeheader()


def load_cache(region, brand):
    create_cache_file()
    results = []

    with CACHE_FILE.open("r", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            if row["search_region"] == region and row["brand"] == brand:
                results.append({
                    "name": row["name"],
                    "address": row["address"],
                    "phone": row["phone"],
                    "link": row["link"],
                    "brand": brand,
                })
    return results


def save_cache(region, brand, results):
    if not results or load_cache(region, brand):
        return

    with CACHE_FILE.open("a", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=CACHE_COLUMNS)
        for center in results:
            writer.writerow({
                "search_region": region,
                "brand": brand,
                "name": center["name"],
                "address": center["address"],
                "phone": center["phone"],
                "link": center["link"],
            })


def search_service_centers(region, brand, limit=5):
    """캐시 또는 카카오맵에서 브랜드 서비스센터를 검색합니다."""

    region = region.strip()
    if not region:
        raise ValueError("검색할 지역을 입력해 주세요.")
    if brand not in BRANDS:
        raise ValueError(f"지원하지 않는 브랜드입니다: {brand}")

    cached = load_cache(region, brand)
    if cached:
        return cached[:limit]

    driver = create_driver()
    try:
        results = crawl_kakao(driver, region, brand, limit)
        searched_region = region

        if not results:
            searched_region = get_broad_region(region)
            if searched_region != region:
                results = load_cache(searched_region, brand)
                if not results:
                    results = crawl_kakao(
                        driver, searched_region, brand, limit,
                    )

        save_cache(searched_region, brand, results)
        return results[:limit]
    finally:
        driver.quit()
