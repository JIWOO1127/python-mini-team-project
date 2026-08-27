import math
import os
import requests
from datetime import datetime, timedelta
from urllib.parse import unquote

KAKAO_API_URL = "https://dapi.kakao.com/v2/local/search/address.json"

KMA_API_URL = (
    "https://apis.data.go.kr/1360000/"
    "VilageFcstInfoService_2.0/getUltraSrtNcst"
)


class TemperatureError(Exception):
    """Raised when the temperature service cannot complete a request."""


def get_location(address):
    """
    주소를 위도, 경도로 변환한다.
    """

    kakao_key = os.getenv("KAKAO_REST_API_KEY")

    if not kakao_key:
        raise TemperatureError(
            "KAKAO_REST_API_KEY 환경변수가 설정되지 않았습니다."
        )

    headers = {
        "Authorization": f"KakaoAK {kakao_key}"
    }

    params = {
        "query": address
    }

    try:
        response = requests.get(
            KAKAO_API_URL,
            headers=headers,
            params=params,
            timeout=10
        )

        response.raise_for_status()

    except requests.Timeout as exc:
        raise TemperatureError(
            "카카오 주소 조회 시간이 초과되었습니다."
        ) from exc
    except requests.RequestException as exc:
        raise TemperatureError(
            "카카오 주소 조회에 실패했습니다. API 키와 네트워크를 확인해 주세요."
        ) from exc

    try:
        data = response.json()
        documents = data["documents"]
    except (ValueError, KeyError, TypeError) as exc:
        raise TemperatureError(
            "카카오 주소 조회 응답 형식이 올바르지 않습니다."
        ) from exc

    if not documents:
        raise TemperatureError("입력한 주소를 찾지 못했습니다.")

    longitude = float(documents[0]["x"])
    latitude = float(documents[0]["y"])

    return latitude, longitude


def convert_to_grid(latitude, longitude):
    """
    위도/경도를 기상청 격자 좌표 nx, ny로 변환한다.
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

    ro = (
        re
        * sf
        / math.pow(ro, sn)
    )

    ra = math.tan(
        math.pi * 0.25
        + latitude * DEGRAD * 0.5
    )

    ra = (
        re
        * sf
        / math.pow(ra, sn)
    )

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


def get_weather_time():
    """
    기상청 API 조회용 날짜와 시간을 만든다.
    """

    now = datetime.now() - timedelta(hours=1)

    base_date = now.strftime("%Y%m%d")
    base_time = now.strftime("%H00")

    return base_date, base_time


def get_temperature(nx, ny):
    """
    기상청 API에서 현재 기온을 가져온다.
    """

    service_key = os.getenv("KMA_SERVICE_KEY")

    if not service_key:
        raise TemperatureError(
            "KMA_SERVICE_KEY 환경변수가 설정되지 않았습니다."
        )

    # 공공데이터포털에서 제공하는 Encoding 키의 중복 URL 인코딩을 방지한다.
    service_key = unquote(service_key)

    base_date, base_time = get_weather_time()

    params = {
        "serviceKey": service_key,
        "pageNo": 1,
        "numOfRows": 100,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny
    }

    try:
        response = requests.get(
            KMA_API_URL,
            params=params,
            timeout=10
        )

        response.raise_for_status()

    except requests.Timeout as exc:
        raise TemperatureError(
            "기상청 날씨 조회 시간이 초과되었습니다."
        ) from exc
    except requests.RequestException as exc:
        raise TemperatureError(
            "기상청 날씨 조회에 실패했습니다. API 키와 네트워크를 확인해 주세요."
        ) from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise TemperatureError(
            "기상청 날씨 응답이 JSON 형식이 아닙니다. 서비스 키를 확인해 주세요."
        ) from exc

    try:
        items = data["response"]["body"]["items"]["item"]

    except (KeyError, TypeError) as exc:
        raise TemperatureError(
            "기상청 날씨 응답 형식이 올바르지 않습니다."
        ) from exc

    for item in items:

        if item["category"] == "T1H":
            return float(item["obsrValue"])

    raise TemperatureError("기상청 응답에서 현재 기온을 찾지 못했습니다.")


def get_current_temperature(address):
    """
    주소를 입력받아 현재 기온을 반환한다.
    """

    location = get_location(address)

    latitude, longitude = location

    nx, ny = convert_to_grid(
        latitude,
        longitude
    )

    temperature = get_temperature(
        nx,
        ny
    )

    return temperature


def recommend_charging_mode(temperature):
    """
    기온에 따라 충전 방식을 추천한다.
    """

    if temperature is None:
        raise TemperatureError("현재 기온이 없어 충전 모드를 추천할 수 없습니다.")

    if temperature >= 30:
        return "slow"

    return "fast"


if __name__ == "__main__":

    address = "경기도 수원시 영통구 영통동"

    temperature = get_current_temperature(
        address
    )

    print("현재 기온:", temperature)

    mode = recommend_charging_mode(
        temperature
    )

    print("추천 충전 방식:", mode)
