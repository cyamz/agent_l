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


def get_daily_weather(location_id: str, days: str = "3d", *, cache: WeatherCache | None = None) -> dict:
    """
    每日天气预报。先查缓存(按日期),未命中请求 API 并按 fxDate 拆分存储。

    Args:
        location_id: 和风 LocationID
        days: 预报天数 3d/7d/10d/15d/30d
        cache: 天气缓存实例(测试注入用),默认用模块级单例

    Returns:
        {"daily": [...], "from_cache": bool} 正常;
        {"error": "...", "daily": []} 出错
    """
    from datetime import date, timedelta

    cache = cache if cache is not None else _weather_cache

    n_days = int(days.rstrip("d"))
    today = date.today()
    want_dates = [(today + timedelta(days=i)).isoformat() for i in range(n_days)]

    # 1. 查缓存(全部日期命中才算)
    cached = cache.get_range(location_id, want_dates)
    if cached is not None:
        return {"daily": cached, "from_cache": True}

    # 2. 请求 API
    try:
        resp = httpx.get(
            f"{_base_url()}/v7/weather/{days}",
            params={"location": location_id, "unit": "m"},
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        return {"error": f"网络请求失败:{e}", "daily": []}

    if str(data.get("code", "")) != "200":
        return {"error": f"和风接口错误: code={data.get('code')}", "daily": []}

    daily = data.get("daily", [])
    # 3. 按 fxDate 拆分写缓存(整批覆盖,容忍少量重复)
    cache.save_daily(location_id, daily)

    # 4. 按请求的日期切片返回
    by_date = {d.get("fxDate"): d for d in daily}
    result = [by_date[d] for d in want_dates if d in by_date]
    return {"daily": result, "from_cache": False}
