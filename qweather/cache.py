"""
qweather 缓存模块:城市缓存(CityCache)与天气缓存(WeatherCache)。

缓存目录:.cache/qweather/{cities,weather}/
- 城市缓存长期有效(地理位置不变)
- 天气缓存按日期有效(当天有效,跨天失效)

@author cy
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

# 项目根:以本模块文件锚定(qweather/cache.py 的上两级),不依赖 cwd
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
# 缓存根目录(项目根下 .cache/qweather)
_CACHE_ROOT = _PROJECT_ROOT / ".cache" / "qweather"
_CITIES_DIR = _CACHE_ROOT / "cities"
_WEATHER_DIR = _CACHE_ROOT / "weather"

# 文件名非法字符(Windows: / \ : * ? " < > |,以及空格)
_ILLEGAL_CHARS = '/\\:*?"<>| '


def _safe_filename(key: str) -> str:
    """
    将缓存 key 转为安全文件名:替换所有文件系统非法字符,过长用 md5 哈希。

    Args:
        key: 原始 key(如 "朝阳|北京|cn")

    Returns:
        安全文件名(不含扩展名)
    """
    cleaned = key
    for ch in _ILLEGAL_CHARS:
        cleaned = cleaned.replace(ch, "_")
    if len(cleaned) <= 64:
        return cleaned
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Any | None:
    """读取 JSON 文件,损坏或不存在返回 None(静默降级)。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _write_json(path: Path, data: Any) -> None:
    """写入 JSON 文件,失败静默(不阻断主流程)。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


class CityCache:
    """城市缓存:长期有效,按查询 key 存储 city-lookup 的 location 数组。"""

    def __init__(self, cities_dir: Path = _CITIES_DIR) -> None:
        self.dir = cities_dir

    def _path(self, location: str, adm: str = "") -> Path:
        key = f"{location}|{adm}|cn"
        return self.dir / f"{_safe_filename(key)}.json"

    def get(self, location: str, adm: str = "") -> list[dict] | None:
        """
        读取城市缓存。

        Returns:
            location 数组;未命中返回 None
        """
        data = _read_json(self._path(location, adm))
        if data is None:
            return None
        return data.get("location")

    def save(self, location: str, adm: str, response: dict) -> None:
        """保存城市缓存(带写入日期,仅作记录)。"""
        _write_json(self._path(location, adm), {
            "location": response.get("location", []),
            "cached_at": date.today().isoformat(),
        })


class WeatherCache:
    """天气缓存:按 location_id + fxDate 存储,当天有效(跨天自然失效)。"""

    def __init__(self, weather_dir: Path = _WEATHER_DIR) -> None:
        self.dir = weather_dir

    def _path(self, location_id: str, fx_date: str) -> Path:
        return self.dir / location_id / f"{fx_date}.json"

    def get(self, location_id: str, fx_date: str) -> dict | None:
        """
        读取某地某日的天气缓存。

        Returns:
            当日 daily 数据;未命中返回 None
        """
        return _read_json(self._path(location_id, fx_date))

    def save_daily(self, location_id: str, daily_list: list[dict]) -> None:
        """
        将 daily 数组按每个 fxDate 拆分存储(3d/7d 请求可共享同一天缓存)。

        Args:
            location_id: 和风 LocationID
            daily_list: API 返回的 daily 数组
        """
        for item in daily_list:
            fx_date = item.get("fxDate")
            if not fx_date:
                continue
            _write_json(self._path(location_id, fx_date), item)

    def get_range(self, location_id: str, dates: list[str]) -> list[dict] | None:
        """
        获取一组日期的缓存,全部命中返回列表,任一缺失返回 None。

        Args:
            location_id: 和风 LocationID
            dates: 需要的日期列表(yyyy-mm-dd)

        Returns:
            全命中返回按 dates 顺序的 daily 列表;任一缺失返回 None
        """
        result = []
        for d in dates:
            item = self.get(location_id, d)
            if item is None:
                return None
            result.append(item)
        return result
