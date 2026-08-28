from __future__ import annotations

import os

import requests

from src.contracts.providers import Coordinates


class ProviderError(RuntimeError):
    """Raised when an external provider cannot satisfy a request."""


class KakaoGeocodingProvider:
    name = "kakao-local"
    endpoint = "https://dapi.kakao.com/v2/local/search/address.json"

    def __init__(self, api_key: str | None = None, timeout: int = 10):
        self.api_key = api_key or os.getenv("KAKAO_REST_API_KEY")
        self.timeout = timeout

    def geocode(self, address: str) -> Coordinates:
        if not address or not address.strip():
            raise ProviderError("주소를 입력해주세요.")
        if not self.api_key:
            raise ProviderError("KAKAO_REST_API_KEY 환경 변수가 설정되지 않았습니다.")
        try:
            response = requests.get(
                self.endpoint,
                params={"query": address.strip()},
                headers={"Authorization": f"KakaoAK {self.api_key}"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            documents = response.json().get("documents", [])
        except (requests.RequestException, ValueError) as exc:
            raise ProviderError("주소 좌표를 조회하지 못했습니다.") from exc
        if not documents:
            raise ProviderError("입력한 주소의 좌표를 찾지 못했습니다.")
        return Coordinates(latitude=float(documents[0]["y"]), longitude=float(documents[0]["x"]))
