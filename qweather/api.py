"""
qweather HTTP 接口封装:城市搜索(lookup_city)与每日预报(get_daily_weather)。
内部自动走缓存。

认证:Authorization: Bearer {QWEATHER_KEY}(JWT)
缓存:.cache/qweather/{cities,weather}/

@author cy
"""
from __future__ import annotations

import httpx

from . import config
from .cache import CityCache, WeatherCache

_city_cache = CityCache()
_weather_cache = WeatherCache()


def _headers() -> dict:
    """构造请求头(JWT Bearer 鉴权)。"""
    return {"Authorization": f"Bearer {config.QWEATHER_KEY}"}


def _base_url() -> str:
    """构造 API 基础 URL。"""
    host = config.QWEATHER_HOST.strip().rstrip("/")
    return f"https://{host}"


def lookup_city(location: str, adm: str = "", *, cache: CityCache | None = None) -> dict:
    """
    城市搜索(仅中国,range=cn)。先查缓存,未命中请求 API。

    Args:
        location: 城市名称/经纬度/LocationID/Adcode
        adm: 上级行政区划(用于排除重名),可选
        cache: 城市缓存实例(测试注入用),默认用模块级单例

    Returns:
        {"location": [...], "from_cache": bool} 正常;
        {"error": "...", "location": []} 出错
    """
    cache = cache if cache is not None else _city_cache

    # 1. 查缓存
    cached = cache.get(location, adm)
    if cached is not None:
        return {"location": cached, "from_cache": True}

    # 2. 请求 API
    params = {"location": location, "range": "cn", "number": 10}
    if adm:
        params["adm"] = adm
    try:
        resp = httpx.get(
            f"{_base_url()}/geo/v2/city/lookup",
            params=params,
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        return {"error": f"网络请求失败:{e}", "location": []}

    if str(data.get("code", "")) != "200":
        return {"error": f"和风接口错误: code={data.get('code')}", "location": []}

    # 3. 写缓存
    cache.save(location, adm, data)
    return {"location": data.get("location", []), "from_cache": False}
