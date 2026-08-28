from unittest.mock import call, patch

import pytest

from src.crawlers import crawler


def test_get_search_locations_returns_detail_to_broad_region():
    assert crawler.get_search_locations("경기도 수원시 영통구 영통동") == [
        "경기도 수원시 영통구 영통동",
        "경기도 수원시 영통구",
        "경기도 수원시",
        "경기도",
    ]


@patch("src.crawlers.crawler._fetch_charging_stations")
def test_detailed_address_falls_back_until_stations_are_found(mock_fetch):
    stations = [{"name": "영통구청 충전소"}]
    mock_fetch.side_effect = [[], [], stations]

    result = crawler.search_charging_stations("경기도 수원시 영통구 영통동")

    assert result == stations
    assert mock_fetch.call_args_list == [
        call("경기도 수원시 영통구 영통동"),
        call("경기도 수원시 영통구"),
        call("경기도 수원시"),
    ]


@patch("src.crawlers.crawler._fetch_charging_stations", return_value=[])
def test_search_raises_after_all_address_levels_are_empty(mock_fetch):
    with pytest.raises(crawler.ChargeCheckError, match="검색된 충전소가 없습니다"):
        crawler.search_charging_stations("경기도 수원시")

    assert mock_fetch.call_args_list == [
        call("경기도 수원시"),
        call("경기도"),
    ]
