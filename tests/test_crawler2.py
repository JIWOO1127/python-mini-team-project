from src.crawlers import crawler2


def test_extract_phone():
    assert crawler2.extract_phone("전화 031-123-4567") == "031-123-4567"


def test_get_broad_region():
    assert crawler2.get_broad_region("경북 경산시") == "경북"
    assert crawler2.get_broad_region("서울") == "서울"


def test_cache_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(
        crawler2,
        "CACHE_FILE",
        tmp_path / "service_center_cache.csv",
    )
    centers = [{
        "name": "테슬라 서비스센터",
        "address": "경기도 수원시",
        "phone": "031-123-4567",
        "link": "https://place.map.kakao.com/1",
        "brand": "Tesla",
    }]

    crawler2.save_cache("경기도 수원시", "Tesla", centers)

    assert crawler2.load_cache("경기도 수원시", "Tesla") == centers
