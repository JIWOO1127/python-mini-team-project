import requests
from bs4 import BeautifulSoup


BASE_URL = "https://chargecheck.kr/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
}

REQUEST_TIMEOUT = 10


class ChargeCheckError(Exception):
    """ChargeCheck 조회 중 발생한 사용자 안내용 예외."""
    pass


def extract_number(text):
    """
    문자열에서 마지막 숫자를 찾아 int로 반환한다.

    예:
    '이용가능 48' -> 48
    '이용가능 급속 14' -> 14
    """

    parts = text.split()

    for part in reversed(parts):
        if part.isdigit():
            return int(part)

    return None


def parse_station(row):
    """
    충전소 HTML 한 행을 dict로 변환한다.
    """

    name_tag = row.select_one("h3")
    address_tag = row.select_one("p.meta")

    station = {
        "name": (
            name_tag.get_text(strip=True)
            if name_tag
            else ""
        ),
        "address": (
            address_tag.get_text(strip=True)
            if address_tag
            else ""
        ),
        "available": None,
        "charging": None,
        "unknown": None,
        "fast_available": None,
        "slow_available": None,
        "detail_url": None,
    }

    badges = row.select(
        ".status-line .badge"
    )

    for badge in badges:

        text = badge.get_text(
            " ",
            strip=True
        )

        # 반드시 '이용가능 급속'을 먼저 검사해야 한다.
        # 그렇지 않으면 '이용가능' 조건에 먼저 걸릴 수 있다.
        if text.startswith("이용가능 급속"):

            station["fast_available"] = (
                extract_number(text)
            )

        elif text.startswith("이용가능"):

            station["available"] = (
                extract_number(text)
            )

        elif text.startswith("충전중"):

            station["charging"] = (
                extract_number(text)
            )

        elif text.startswith("미확인"):

            station["unknown"] = (
                extract_number(text)
            )

    href = row.get("href")

    if href:
        station["detail_url"] = (
            "https://chargecheck.kr"
            + href
        )

    # -----------------------------
    # 완속 이용가능 충전기 수 계산
    # -----------------------------

    available = station.get("available")
    fast_available = station.get(
        "fast_available"
    )

    if (
        available is not None
        and fast_available is not None
    ):
        station["slow_available"] = max(
            available - fast_available,
            0
        )

    return station


def parse_charging_stations(html):
    """
    ChargeCheck HTML에서 충전소 목록을 파싱한다.

    Returns
    -------
    list[dict]
    """

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    station_rows = soup.select(
        "a.station-row"
    )

    stations = []

    for row in station_rows:

        station = parse_station(row)

        # 이름 없는 데이터는 제외
        if station["name"]:
            stations.append(station)

    return stations


def search_charging_stations(location):
    """
    ChargeCheck에서 입력한 위치의
    전기차 충전소를 검색한다.

    Parameters
    ----------
    location : str
        예:
        '경기도 수원시 영통구 영통동'

    Returns
    -------
    list[dict]
        충전소 정보 목록
    """

    location = location.strip()

    if not location:
        raise ChargeCheckError(
            "검색할 위치를 입력해주세요."
        )

    params = {
        "q": location
    }

    try:

        response = requests.get(
            BASE_URL,
            params=params,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

    except requests.Timeout as exc:

        raise ChargeCheckError(
            "충전소 조회 시간이 초과되었습니다."
        ) from exc

    except requests.RequestException as exc:

        raise ChargeCheckError(
            "충전소 정보를 불러오지 못했습니다."
        ) from exc

    stations = parse_charging_stations(
        response.text
    )

    if not stations:
        raise ChargeCheckError(
            "검색된 충전소가 없습니다."
        )

    return stations


def filter_slow_stations(stations):
    """
    완속 충전이 가능한 충전소만 반환한다.

    완속 이용가능 충전기 수가 많은 순서로 정렬한다.
    """

    slow_stations = [
        station
        for station in stations
        if (
            station.get("slow_available")
            or 0
        ) > 0
    ]

    slow_stations.sort(
        key=lambda station: (
            station.get("slow_available")
            or 0
        ),
        reverse=True
    )

    return slow_stations


def filter_fast_stations(stations):
    """
    급속 충전이 가능한 충전소만 반환한다.

    급속 이용가능 충전기 수가 많은 순서로 정렬한다.
    """

    fast_stations = [
        station
        for station in stations
        if (
            station.get("fast_available")
            or 0
        ) > 0
    ]

    fast_stations.sort(
        key=lambda station: (
            station.get("fast_available")
            or 0
        ),
        reverse=True
    )

    return fast_stations


def recommend_stations(
    stations,
    mode="slow",
    limit=3
):
    """
    충전 방식에 따라 추천 충전소를 반환한다.

    Parameters
    ----------
    stations : list[dict]
        전체 충전소 목록

    mode : str
        'slow' 또는 'fast'

    limit : int
        반환할 최대 충전소 개수

    Returns
    -------
    list[dict]
    """

    if mode == "slow":

        filtered = filter_slow_stations(
            stations
        )

    elif mode == "fast":

        filtered = filter_fast_stations(
            stations
        )

    else:

        filtered = stations

    return filtered[:limit]


if __name__ == "__main__":

    location = (
        "경기도 수원시 영통구 영통동"
    )

    try:

        stations = (
            search_charging_stations(
                location
            )
        )

        print(
            f"검색 결과: {len(stations)}개"
        )

        print(
            "\n--- 검색 결과 일부 ---"
        )

        for station in stations[:5]:

            print(
                station
            )

        print(
            "\n--- 완속 추천 TOP 3 ---"
        )

        slow_recommendations = (
            recommend_stations(
                stations,
                mode="slow",
                limit=3
            )
        )

        for station in slow_recommendations:

            print(
                station["name"],
                "| 완속:",
                station["slow_available"],
                "| 급속:",
                station["fast_available"]
            )

        print(
            "\n--- 급속 추천 TOP 3 ---"
        )

        fast_recommendations = (
            recommend_stations(
                stations,
                mode="fast",
                limit=3
            )
        )

        for station in fast_recommendations:

            print(
                station["name"],
                "| 완속:",
                station["slow_available"],
                "| 급속:",
                station["fast_available"]
            )

    except ChargeCheckError as exc:

        print(
            f"오류: {exc}"
        )