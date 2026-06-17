"""api 模块测试(mock httpx,缓存通过参数注入避免单例污染)。"""
from unittest.mock import patch, MagicMock

import qweather.api as api
from qweather.cache import CityCache, WeatherCache


def _mock_response(json_data, status=200):
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.status_code = status
    resp.raise_for_status = MagicMock()  # 默认不抛
    return resp


def test_lookup_city_uses_cache(tmp_path):
    cache = CityCache(tmp_path / "cities")
    cache.save("北京", "", {"location": [{"name": "北京", "id": "101010100"}]})

    result = api.lookup_city("北京", cache=cache)
    assert result["location"] == [{"name": "北京", "id": "101010100"}]
    assert result["from_cache"] is True


def test_lookup_city_requests_and_caches(tmp_path):
    cache = CityCache(tmp_path / "cities")
    api_data = {"code": "200", "location": [{"name": "上海", "id": "101020100"}]}
    with patch("qweather.api.httpx.get", return_value=_mock_response(api_data)) as mock_get:
        result = api.lookup_city("上海", cache=cache)

    assert result["location"] == [{"name": "上海", "id": "101020100"}]
    assert result["from_cache"] is False
    call = mock_get.call_args
    assert call.kwargs["params"]["range"] == "cn"
    assert call.kwargs["params"]["location"] == "上海"
    # 已写入注入的缓存
    assert cache.get("上海") == [{"name": "上海", "id": "101020100"}]


def test_lookup_city_adm_passed(tmp_path):
    cache = CityCache(tmp_path / "cities")
    with patch("qweather.api.httpx.get", return_value=_mock_response({"code": "200", "location": []})) as mock_get:
        api.lookup_city("朝阳", adm="北京", cache=cache)
    assert mock_get.call_args.kwargs["params"]["adm"] == "北京"


def test_lookup_city_business_error(tmp_path):
    cache = CityCache(tmp_path / "cities")
    with patch("qweather.api.httpx.get", return_value=_mock_response({"code": "404"})):
        result = api.lookup_city("不存在", cache=cache)
    assert "error" in result
    assert result["location"] == []


def test_lookup_city_network_error(tmp_path):
    import httpx
    cache = CityCache(tmp_path / "cities")
    with patch("qweather.api.httpx.get", side_effect=httpx.ConnectError("fail")):
        result = api.lookup_city("北京", cache=cache)
    assert "网络请求失败" in result["error"]
    assert result["location"] == []


def test_get_daily_weather_requests_and_caches(tmp_path):
    import datetime as dt
    cache = WeatherCache(tmp_path / "weather")
    today = dt.date.today()
    dates = [(today + dt.timedelta(days=i)).isoformat() for i in range(3)]
    daily = [
        {"fxDate": dates[i], "tempMax": str(30 - i), "textDay": "晴"}
        for i in range(3)
    ]
    with patch("qweather.api.httpx.get", return_value=_mock_response({"code": "200", "daily": daily})) as mock_get:
        result = api.get_daily_weather("101010100", "3d", cache=cache)

    assert result["from_cache"] is False
    assert [d["fxDate"] for d in result["daily"]] == dates
    # URL 路径含 days
    assert "/v7/weather/3d" in mock_get.call_args.args[0]
    # 已按 fxDate 拆分写入注入的缓存
    assert cache.get("101010100", dates[0])["textDay"] == "晴"


def test_get_daily_weather_cache_hit(tmp_path):
    import datetime as dt
    cache = WeatherCache(tmp_path / "weather")
    today = dt.date.today()
    dates = [(today + dt.timedelta(days=i)).isoformat() for i in range(3)]
    cache.save_daily("101010100", [{"fxDate": d, "tempMax": "20"} for d in dates])

    with patch("qweather.api.httpx.get") as mock_get:
        result = api.get_daily_weather("101010100", "3d", cache=cache)

    assert result["from_cache"] is True
    assert mock_get.call_count == 0  # 未请求 API
    assert len(result["daily"]) == 3


def test_get_daily_weather_business_error(tmp_path):
    cache = WeatherCache(tmp_path / "weather")
    with patch("qweather.api.httpx.get", return_value=_mock_response({"code": "402"})):
        result = api.get_daily_weather("101010100", "3d", cache=cache)
    assert "和风接口错误" in result["error"]
    assert result["daily"] == []
