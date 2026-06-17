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
