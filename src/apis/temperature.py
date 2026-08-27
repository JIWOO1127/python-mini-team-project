"""사용자 주소를 기준으로 현재 기온을 조회합니다."""

from __future__ import annotations

import math
import os
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import unquote

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


KAKAO_API_URL = "https://dapi.kakao.com/v2/local/search/address.json"

KMA_API_URL = (
    "https://apis.data.go.kr/1360000/"
    "VilageFcstInfoService_2.0/getUltraSrtNcst"
)

REQUEST_TIMEOUT = 10


class TemperatureError(Exception):
    """기온 조회 중 발생한 사용자 안내용 오류입니다."""


def geocode_address(address: str) -> tuple[float, float]:
    """
    주소를 위도, 경도로 변환합니다.

    Returns:
        (latitude, longitude)
    """

    address = address.strip()

    if not address:
        raise TemperatureError("현재 위치를 입력해 주세요.")

    kakao_key = os.getenv("KAKAO_REST_API_KEY")

    if not kakao_key:
        raise TemperatureError(
            "KAKAO_REST_API_KEY 환경변수가 설정되지 않았습니다."
        )

    try:
        response = requests.get(
            KAKAO_API_URL,
            params={"query": address},
            headers={
                "Authorization": f"KakaoAK {kakao_key}"
            },
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

    except requests.Timeout as exc:
        raise TemperatureError(
            "주소 좌표 조회 시간이 초과되었습니다."
        ) from exc

    except requests.HTTPError as exc:
        try:
            error_data = response.json()
        except ValueError:
            error_data = {}

        error_code = error_data.get("code")

        if response.status_code == 403 and error_code == -3:
            message = (
                "카카오 로컬 API 호출 권한이 없습니다. "
                "Kakao Developers에서 해당 앱의 로컬 API 사용 설정을 확인해 주세요."
            )
        else:
            message = (
                "카카오 주소 검색에 실패했습니다. "
                f"(HTTP {response.status_code}, code: {error_code})"
            )

        raise TemperatureError(message) from exc

    except requests.RequestException as exc:
        raise TemperatureError(
            "주소 좌표를 조회하지 못했습니다."
        ) from exc

    try:
        documents = response.json().get("documents", [])
    except ValueError as exc:
        raise TemperatureError(
            "카카오 주소 검색 응답 형식이 올바르지 않습니다."
        ) from exc

    if not documents:
        raise TemperatureError(
            "입력한 주소의 좌표를 찾지 못했습니다."
        )

    longitude = float(documents[0]["x"])
    latitude = float(documents[0]["y"])

    return latitude, longitude


def convert_to_grid(
    latitude: float,
    longitude: float
) -> tuple[int, int]:
    """
    위도/경도를 기상청 격자 좌표(nx, ny)로 변환합니다.

    기상청 DFS 격자 변환 공식을 사용합니다.
    """

    RE = 6371.00877
    GRID = 5.0

    SLAT1 = 30.0
    SLAT2 = 60.0

    OLON = 126.0
    OLAT = 38.0

    XO = 43
    YO = 136

    DEGRAD = math.pi / 180.0

    re = RE / GRID

    slat1 = SLAT1 * DEGRAD
    slat2 = SLAT2 * DEGRAD

    olon = OLON * DEGRAD
    olat = OLAT * DEGRAD

    sn = math.tan(
        math.pi * 0.25 + slat2 * 0.5
    ) / math.tan(
        math.pi * 0.25 + slat1 * 0.5
    )

    sn = math.log(
        math.cos(slat1) / math.cos(slat2)
    ) / math.log(sn)

    sf = math.tan(
        math.pi * 0.25 + slat1 * 0.5
    )

    sf = (
        math.pow(sf, sn)
        * math.cos(slat1)
        / sn
    )

    ro = math.tan(
        math.pi * 0.25 + olat * 0.5
    )

    ro = re * sf / math.pow(ro, sn)

    ra = math.tan(
        math.pi * 0.25
        + latitude * DEGRAD * 0.5
    )

    ra = re * sf / math.pow(ra, sn)

    theta = longitude * DEGRAD - olon

    if theta > math.pi:
        theta -= 2.0 * math.pi

    if theta < -math.pi:
        theta += 2.0 * math.pi

    theta *= sn

    nx = int(
        math.floor(
            ra * math.sin(theta)
            + XO
            + 0.5
        )
    )

    ny = int(
        math.floor(
            ro
            - ra * math.cos(theta)
            + YO
            + 0.5
        )
    )

    return nx, ny


def get_base_datetime() -> tuple[str, str]:
    """
    초단기실황 조회에 사용할 base_date/base_time을 계산합니다.

    최근 관측값을 안정적으로 조회하기 위해
    현재 시각에서 약 1시간 전 기준으로 요청합니다.
    """

    now = datetime.now() - timedelta(hours=1)

    base_date = now.strftime("%Y%m%d")
    base_time = now.strftime("%H00")

    return base_date, base_time


def fetch_temperature(
    nx: int,
    ny: int
) -> float:
    """
    기상청 초단기실황에서 현재 기온(T1H)을 가져옵니다.
    """

    service_key = os.getenv("KMA_SERVICE_KEY")

    if not service_key:
        raise TemperatureError(
            "KMA_SERVICE_KEY 환경변수가 설정되지 않았습니다."
        )

    # 공공데이터포털에서 제공하는 Encoding 키도 requests에서 사용할 수 있게 한다.
    service_key = unquote(service_key)

    base_date, base_time = get_base_datetime()

    params = {
        "serviceKey": service_key,
        "pageNo": 1,
        "numOfRows": 100,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    }

    try:
        response = requests.get(
            KMA_API_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

    except (
        requests.RequestException,
        ValueError
    ) as exc:
        raise TemperatureError(
            "기상청 날씨 정보를 불러오지 못했습니다."
        ) from exc

    try:
        items = (
            data["response"]["body"]["items"]["item"]
        )
    except (KeyError, TypeError):
        raise TemperatureError(
            "기상청 API 응답 형식이 올바르지 않습니다."
        )

    for item in items:
        if item.get("category") == "T1H":
            return float(
                item["obsrValue"]
            )

    raise TemperatureError(
        "현재 기온 정보를 찾지 못했습니다."
    )


def get_current_temperature(
    address: str
) -> float:
    """
    주소를 받아 현재 기온을 반환합니다.

    address
        ↓
    위도/경도
        ↓
    기상청 nx/ny
        ↓
    현재 기온
    """

    latitude, longitude = geocode_address(
        address
    )

    nx, ny = convert_to_grid(
        latitude,
        longitude
    )

    return fetch_temperature(
        nx,
        ny
    )


def recommend_charging_mode(
    temperature: float
) -> str:
    """
    외기온도를 기준으로 간단한 충전 모드를 추천합니다.

    주의:
    현재 기준은 프로젝트 데모용 rule입니다.
    추후 배터리 모델 또는 근거 기반 기준으로 교체할 수 있습니다.
    """

    if temperature >= 30:
        return "slow"

    return "fast"

if __name__ == "__main__":
    temperature = get_current_temperature(
        "경기도 수원시 영통구 영통동"
    )

    print("현재 기온:", temperature)
