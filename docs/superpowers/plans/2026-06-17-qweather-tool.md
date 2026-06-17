# 和风天气工具(qweather 包)实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现一个基于 OpenAI tool calling 的和风天气查询工具,持续聊天,支持城市多轮确认与穿衣建议,带两类缓存。

**Architecture:** `qweather/` 包四层分离(config/cache/api/agent),两个工具(get_city/get_daily_weather)内部走缓存,AI 不感知缓存;持续聊天 + 内层工具循环;城市缓存长期有效,天气缓存按日期当天有效。

**Tech Stack:** Python 3.10+、openai(SDK,调 DeepSeek)、httpx(和风 HTTP)、PyJWT/cryptography(鉴权,脚本已就位)、python-dotenv、pytest(测试)。

**Spec:** `docs/superpowers/specs/2026-06-17-qweather-tool-design.md`

**鉴权前置**:`scripts/gen_qweather_jwt.py` 已就位;`.env` 的 `QWEATHER_KEY` 需为和风控制台生成的 JWT token。

---

## File Structure

```
qweather/
├── __init__.py        # 再导出 lookup_city/get_daily_weather/CityCache/WeatherCache/run_chat
├── config.py          # 读 env + check_config() 启动校验
├── cache.py           # CityCache(长期) + WeatherCache(按日期)
├── api.py             # lookup_city / get_daily_weather(httpx + 缓存)
└── agent.py           # TOOLS 定义 + run_tool 分发 + run_chat 主循环 + SYSTEM_PROMPT
tests/
├── test_config.py
├── test_cache.py
└── test_api.py
01_tool_calling_real.py  # 精简入口
```

缓存目录(运行时生成,已 gitignore):
```
.cache/qweather/{cities,weather}/
```

---

## Task 1: 包骨架与配置模块(config.py)

**Files:**
- Create: `qweather/__init__.py`(占位,Task 6 补再导出)
- Create: `qweather/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: 写失败测试 — check_config 检测缺失/占位符**

`tests/test_config.py`:
```python
"""config 模块测试。"""
import importlib
import os


def _reload_config(monkeypatch, env):
    """用指定 env 重载 config 模块。"""
    for k in ["DEEPSEEK_API_KEY", "QWEATHER_HOST", "QWEATHER_KEY"]:
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    import qweather.config as config
    importlib.reload(config)
    return config


def test_check_config_missing_exits(monkeypatch, capsys):
    config = _reload_config(monkeypatch, {})
    try:
        config.check_config()
        assert False, "应抛 SystemExit"
    except SystemExit:
        out = capsys.readouterr().out
        assert "DEEPSEEK_API_KEY" in out
        assert "QWEATHER_HOST" in out
        assert "QWEATHER_KEY" in out


def test_check_config_placeholder_exits(monkeypatch, capsys):
    config = _reload_config(monkeypatch, {
        "DEEPSEEK_API_KEY": "your_deepseek_api_key_here",
        "QWEATHER_HOST": "your_qweather_host_here",
        "QWEATHER_KEY": "your_qweather_jwt_token_here",
    })
    try:
        config.check_config()
        assert False, "占位符应抛 SystemExit"
    except SystemExit:
        assert "缺少配置" in capsys.readouterr().out


def test_check_config_ok(monkeypatch):
    config = _reload_config(monkeypatch, {
        "DEEPSEEK_API_KEY": "sk-real",
        "QWEATHER_HOST": "xxx.qweatherapi.com",
        "QWEATHER_KEY": "eyJrealjwt",
    })
    config.check_config()  # 不抛即通过
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL(`ModuleNotFoundError: qweather.config`)

- [ ] **Step 3: 实现包骨架与 config**

`qweather/__init__.py`(占位,Task 6 补全):
```python
"""qweather 包:和风天气查询工具(基于 OpenAI tool calling)。"""
```

`qweather/config.py`:
```python
"""
qweather 配置模块:集中读取 .env 并提供启动校验。

@author cy
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# 和风天气配置
QWEATHER_HOST = os.getenv("QWEATHER_HOST", "")
QWEATHER_KEY = os.getenv("QWEATHER_KEY", "")

# DeepSeek 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")


def _is_placeholder(value: str) -> bool:
    """判断值是否仍是 .env.example 里的占位符。"""
    return value.startswith("your_") or value.endswith("_here")


def check_config() -> None:
    """
    启动校验:确保必要配置已正确填写(非空且非占位符)。

    Raises:
        SystemExit: 缺失关键配置时,打印提示并退出
    """
    missing = []
    if not DEEPSEEK_API_KEY or _is_placeholder(DEEPSEEK_API_KEY):
        missing.append("DEEPSEEK_API_KEY")
    if not QWEATHER_HOST or _is_placeholder(QWEATHER_HOST):
        missing.append("QWEATHER_HOST")
    if not QWEATHER_KEY or _is_placeholder(QWEATHER_KEY):
        missing.append("QWEATHER_KEY")
    if missing:
        print(f"[错误] 缺少配置:{', '.join(missing)}")
        print("请在 .env 中配置(参考 .env.example)")
        sys.exit(1)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/test_config.py -v`
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add qweather/__init__.py qweather/config.py tests/test_config.py
git commit -m "feat(qweather): 配置模块与启动校验"
```

---

## Task 2: 缓存通用工具与 CityCache

**Files:**
- Create: `qweather/cache.py`
- Create: `tests/test_cache.py`

- [ ] **Step 1: 写失败测试 — 通用工具与 CityCache**

`tests/test_cache.py`:
```python
"""cache 模块测试。"""
from pathlib import Path

from qweather.cache import _safe_filename, CityCache


def test_safe_filename_short():
    assert _safe_filename("朝阳|北京|cn") == "朝阳|北京|cn"


def test_safe_filename_strips_slashes():
    assert "/" not in _safe_filename("a/b\\c d")
    assert "\\" not in _safe_filename("a/b\\c d")
    assert " " not in _safe_filename("a/b\\c d")


def test_safe_filename_long_hashes():
    key = "x" * 200
    name = _safe_filename(key)
    assert len(name) == 32  # md5 hex


def test_city_cache_miss(tmp_path):
    cache = CityCache(tmp_path / "cities")
    assert cache.get("不存在的地方") is None


def test_city_cache_roundtrip(tmp_path):
    cache = CityCache(tmp_path / "cities")
    resp = {"location": [{"name": "北京", "id": "101010100"}]}
    cache.save("北京", "", resp)
    got = cache.get("北京", "")
    assert got == [{"name": "北京", "id": "101010100"}]


def test_city_cache_key_includes_adm(tmp_path):
    cache = CityCache(tmp_path / "cities")
    cache.save("朝阳", "北京", {"location": [{"name": "朝阳", "id": "1"}]})
    cache.save("朝阳", "辽宁", {"location": [{"name": "朝阳", "id": "2"}]})
    assert cache.get("朝阳", "北京") == [{"name": "朝阳", "id": "1"}]
    assert cache.get("朝阳", "辽宁") == [{"name": "朝阳", "id": "2"}]


def test_city_cache_corrupt_file_returns_none(tmp_path):
    cache = CityCache(tmp_path / "cities")
    path = cache._path("北京", "")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not json", encoding="utf-8")
    assert cache.get("北京", "") is None
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/test_cache.py -v`
Expected: FAIL(`ModuleNotFoundError` / `ImportError`)

- [ ] **Step 3: 实现通用工具与 CityCache**

`qweather/cache.py`:
```python
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

# 缓存根目录(项目根下 .cache/qweather)
_CACHE_ROOT = Path(".cache/qweather")
_CITIES_DIR = _CACHE_ROOT / "cities"
_WEATHER_DIR = _CACHE_ROOT / "weather"


def _safe_filename(key: str) -> str:
    """
    将缓存 key 转为安全文件名:去除非法字符,过长用 md5 哈希。

    Args:
        key: 原始 key(如 "朝阳|北京|cn")

    Returns:
        安全文件名(不含扩展名)
    """
    cleaned = key.replace("/", "_").replace("\\", "_").replace(" ", "")
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
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/test_cache.py -v`
Expected: 7 passed

- [ ] **Step 5: 提交**

```bash
git add qweather/cache.py tests/test_cache.py
git commit -m "feat(qweather): 缓存通用工具与 CityCache"
```

---

## Task 3: WeatherCache(按日期,当天有效)

**Files:**
- Modify: `qweather/cache.py`(追加 WeatherCache)
- Modify: `tests/test_cache.py`(追加测试)

- [ ] **Step 1: 写失败测试 — WeatherCache**

追加到 `tests/test_cache.py`:
```python
from qweather.cache import WeatherCache


def test_weather_cache_miss(tmp_path):
    cache = WeatherCache(tmp_path / "weather")
    assert cache.get("101010100", "2026-06-17") is None


def test_weather_cache_save_daily_splits_by_fxdate(tmp_path):
    cache = WeatherCache(tmp_path / "weather")
    daily = [
        {"fxDate": "2026-06-17", "tempMax": "30"},
        {"fxDate": "2026-06-18", "tempMax": "28"},
    ]
    cache.save_daily("101010100", daily)
    assert cache.get("101010100", "2026-06-17") == {"fxDate": "2026-06-17", "tempMax": "30"}
    assert cache.get("101010100", "2026-06-18") == {"fxDate": "2026-06-18", "tempMax": "28"}


def test_weather_cache_get_range_all_hit(tmp_path):
    cache = WeatherCache(tmp_path / "weather")
    cache.save_daily("1", [{"fxDate": "2026-06-17"}, {"fxDate": "2026-06-18"}])
    result = cache.get_range("1", ["2026-06-17", "2026-06-18"])
    assert [d["fxDate"] for d in result] == ["2026-06-17", "2026-06-18"]


def test_weather_cache_get_range_partial_miss_returns_none(tmp_path):
    cache = WeatherCache(tmp_path / "weather")
    cache.save_daily("1", [{"fxDate": "2026-06-17"}])
    assert cache.get_range("1", ["2026-06-17", "2026-06-18"]) is None


def test_weather_cache_skips_item_without_fxdate(tmp_path):
    cache = WeatherCache(tmp_path / "weather")
    cache.save_daily("1", [{"tempMax": "30"}])  # 无 fxDate
    # 不应抛错,文件不创建
    assert list((tmp_path / "weather" / "1").glob("*.json")) == []
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/test_cache.py::test_weather_cache_miss -v`
Expected: FAIL(`ImportError: cannot import name 'WeatherCache'`)

- [ ] **Step 3: 实现 WeatherCache**

追加到 `qweather/cache.py` 末尾:
```python
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
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/test_cache.py -v`
Expected: 12 passed(7 + 5)

- [ ] **Step 5: 提交**

```bash
git add qweather/cache.py tests/test_cache.py
git commit -m "feat(qweather): WeatherCache 按日期存储与当天有效判断"
```

---

## Task 4: api.py — lookup_city(httpx + 城市缓存)

**Files:**
- Create: `qweather/api.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: 写失败测试 — lookup_city 缓存命中 + API 解析 + 错误**

`tests/test_api.py`:
```python
"""api 模块测试(mock httpx)。"""
from unittest.mock import patch, MagicMock

import qweather.api as api


def _mock_response(json_data, status=200):
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.status_code = status
    return resp


def test_lookup_city_uses_cache(tmp_path, monkeypatch):
    # 指向临时缓存目录,先写入再读
    from qweather import cache as cachemod
    monkeypatch.setattr(cachemod, "_CITIES_DIR", tmp_path / "cities")
    monkeypatch.setattr(api, "_city_cache", cachemod.CityCache(tmp_path / "cities"))
    api._city_cache.save("北京", "", {"location": [{"name": "北京", "id": "101010100"}]})

    result = api.lookup_city("北京")
    assert result["location"] == [{"name": "北京", "id": "101010100"}]
    assert result["from_cache"] is True


def test_lookup_city_requests_and_caches(tmp_path, monkeypatch):
    from qweather import cache as cachemod
    monkeypatch.setattr(api, "_city_cache", cachemod.CityCache(tmp_path / "cities"))

    api_data = {"code": "200", "location": [{"name": "上海", "id": "101020100"}]}
    with patch("qweather.api.httpx.get", return_value=_mock_response(api_data)) as mock_get:
        result = api.lookup_city("上海")

    assert result["location"] == [{"name": "上海", "id": "101020100"}]
    assert result["from_cache"] is False
    # 参数含 range=cn
    call = mock_get.call_args
    assert call.kwargs["params"]["range"] == "cn"
    assert call.kwargs["params"]["location"] == "上海"
    # 已写入缓存
    assert api._city_cache.get("上海") == [{"name": "上海", "id": "101020100"}]


def test_lookup_city_adm_passed(tmp_path, monkeypatch):
    from qweather import cache as cachemod
    monkeypatch.setattr(api, "_city_cache", cachemod.CityCache(tmp_path / "cities"))
    with patch("qweather.api.httpx.get", return_value=_mock_response({"code": "200", "location": []})) as mock_get:
        api.lookup_city("朝阳", adm="北京")
    assert mock_get.call_args.kwargs["params"]["adm"] == "北京"


def test_lookup_city_business_error(tmp_path, monkeypatch):
    from qweather import cache as cachemod
    monkeypatch.setattr(api, "_city_cache", cachemod.CityCache(tmp_path / "cities"))
    with patch("qweather.api.httpx.get", return_value=_mock_response({"code": "404"})):
        result = api.lookup_city("不存在")
    assert "error" in result
    assert result["location"] == []


def test_lookup_city_network_error(tmp_path, monkeypatch):
    import httpx
    from qweather import cache as cachemod
    monkeypatch.setattr(api, "_city_cache", cachemod.CityCache(tmp_path / "cities"))
    with patch("qweather.api.httpx.get", side_effect=httpx.ConnectError("fail")):
        result = api.lookup_city("北京")
    assert "网络请求失败" in result["error"]
    assert result["location"] == []
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/test_api.py -v`
Expected: FAIL(`ModuleNotFoundError: qweather.api`)

- [ ] **Step 3: 实现 api.py 的 HTTP 基础 + lookup_city**

`qweather/api.py`:
```python
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


def lookup_city(location: str, adm: str = "") -> dict:
    """
    城市搜索(仅中国,range=cn)。先查缓存,未命中请求 API。

    Args:
        location: 城市名称/经纬度/LocationID/Adcode
        adm: 上级行政区划(用于排除重名),可选

    Returns:
        {"location": [...], "from_cache": bool} 正常;
        {"error": "...", "location": []} 出错
    """
    # 1. 查缓存
    cached = _city_cache.get(location, adm)
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
        data = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        return {"error": f"网络请求失败:{e}", "location": []}

    if str(data.get("code", "")) != "200":
        return {"error": f"和风接口错误: code={data.get('code')}", "location": []}

    # 3. 写缓存
    _city_cache.save(location, adm, data)
    return {"location": data.get("location", []), "from_cache": False}
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/test_api.py -v`
Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git add qweather/api.py tests/test_api.py
git commit -m "feat(qweather): lookup_city 城市搜索(httpx + 城市缓存)"
```

---

## Task 5: api.py — get_daily_weather(httpx + 天气缓存)

**Files:**
- Modify: `qweather/api.py`(追加 get_daily_weather)
- Modify: `tests/test_api.py`(追加测试)

- [ ] **Step 1: 写失败测试 — get_daily_weather**

追加到 `tests/test_api.py`:
```python
def test_get_daily_weather_requests_and_caches(tmp_path, monkeypatch):
    from qweather import cache as cachemod
    monkeypatch.setattr(api, "_weather_cache", cachemod.WeatherCache(tmp_path / "weather"))

    daily = [
        {"fxDate": "2026-06-17", "tempMax": "30", "textDay": "晴"},
        {"fxDate": "2026-06-18", "tempMax": "28", "textDay": "多云"},
        {"fxDate": "2026-06-19", "tempMax": "27", "textDay": "阴"},
    ]
    with patch("qweather.api.httpx.get", return_value=_mock_response({"code": "200", "daily": daily})) as mock_get:
        result = api.get_daily_weather("101010100", "3d")

    assert result["from_cache"] is False
    assert [d["fxDate"] for d in result["daily"]] == ["2026-06-17", "2026-06-18", "2026-06-19"]
    # URL 路径含 days
    assert "/v7/weather/3d" in mock_get.call_args.args[0]
    # 已按 fxDate 拆分写入缓存
    assert api._weather_cache.get("101010100", "2026-06-17")["textDay"] == "晴"


def test_get_daily_weather_cache_hit(tmp_path, monkeypatch):
    from qweather import cache as cachemod
    monkeypatch.setattr(api, "_weather_cache", cachemod.WeatherCache(tmp_path / "weather"))
    # 预先写入今天起 3 天
    import datetime as dt
    today = dt.date.today()
    dates = [(today + dt.timedelta(days=i)).isoformat() for i in range(3)]
    api._weather_cache.save_daily("101010100", [{"fxDate": d, "tempMax": "20"} for d in dates])

    with patch("qweather.api.httpx.get") as mock_get:
        result = api.get_daily_weather("101010100", "3d")

    assert result["from_cache"] is True
    assert mock_get.call_count == 0  # 未请求 API
    assert len(result["daily"]) == 3


def test_get_daily_weather_business_error(tmp_path, monkeypatch):
    from qweather import cache as cachemod
    monkeypatch.setattr(api, "_weather_cache", cachemod.WeatherCache(tmp_path / "weather"))
    with patch("qweather.api.httpx.get", return_value=_mock_response({"code": "402"})):
        result = api.get_daily_weather("101010100", "3d")
    assert "和风接口错误" in result["error"]
    assert result["daily"] == []
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/test_api.py::test_get_daily_weather_requests_and_caches -v`
Expected: FAIL(`AttributeError: get_daily_weather`)

- [ ] **Step 3: 实现 get_daily_weather**

追加到 `qweather/api.py` 末尾:
```python
def get_daily_weather(location_id: str, days: str = "3d") -> dict:
    """
    每日天气预报。先查缓存(按日期),未命中请求 API 并按 fxDate 拆分存储。

    Args:
        location_id: 和风 LocationID
        days: 预报天数 3d/7d/10d/15d/30d

    Returns:
        {"daily": [...], "from_cache": bool} 正常;
        {"error": "...", "daily": []} 出错
    """
    from datetime import date, timedelta

    n_days = int(days.rstrip("d"))
    today = date.today()
    want_dates = [(today + timedelta(days=i)).isoformat() for i in range(n_days)]

    # 1. 查缓存(全部日期命中才算)
    cached = _weather_cache.get_range(location_id, want_dates)
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
        data = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        return {"error": f"网络请求失败:{e}", "daily": []}

    if str(data.get("code", "")) != "200":
        return {"error": f"和风接口错误: code={data.get('code')}", "daily": []}

    daily = data.get("daily", [])
    # 3. 按 fxDate 拆分写缓存(整批覆盖,容忍少量重复)
    _weather_cache.save_daily(location_id, daily)

    # 4. 按请求的日期切片返回
    by_date = {d.get("fxDate"): d for d in daily}
    result = [by_date[d] for d in want_dates if d in by_date]
    return {"daily": result, "from_cache": False}
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/test_api.py -v`
Expected: 8 passed(5 + 3)

- [ ] **Step 5: 提交**

```bash
git add qweather/api.py tests/test_api.py
git commit -m "feat(qweather): get_daily_weather 每日预报(httpx + 天气缓存)"
```

---

## Task 6: agent.py — 工具定义 + run_tool + run_chat

> 说明:Agent 的 run_chat 涉及真实 AI 调用,不便单测;本任务对纯逻辑的 run_tool(分发+精简)做测试,run_chat 用 Task 7 端到端手动验证。

**Files:**
- Create: `qweather/agent.py`
- Modify: `qweather/__init__.py`(补再导出)
- Create: `tests/test_agent.py`

- [ ] **Step 1: 写失败测试 — run_tool 分发与精简**

`tests/test_agent.py`:
```python
"""agent 模块测试(仅 run_tool 分发逻辑)。"""
from unittest.mock import patch

from qweather import agent


def test_run_tool_get_city_slim_fields():
    with patch.object(agent, "lookup_city", return_value={
        "location": [{"name": "北京", "id": "101010100", "adm1": "北京市", "lat": "39.9", "lon": "116.4", "rank": "10", "extra": "ignored"}]
    }):
        out = agent.run_tool("get_city", {"query": "北京"})
    import json
    data = json.loads(out)
    assert data["count"] == 1
    c = data["candidates"][0]
    assert c["name"] == "北京"
    assert c["id"] == "101010100"
    assert "extra" not in c  # 精简掉无关字段


def test_run_tool_get_city_empty():
    with patch.object(agent, "lookup_city", return_value={"location": []}):
        out = agent.run_tool("get_city", {"query": "不存在"})
    import json
    assert json.loads(out)["count"] == 0


def test_run_tool_get_daily_weather_slim():
    with patch.object(agent, "get_daily_weather", return_value={
        "daily": [{"fxDate": "2026-06-17", "tempMax": "30", "textDay": "晴", "cloud": "10", "wind360Day": "45"}]
    }):
        out = agent.run_tool("get_daily_weather", {"location_id": "101010100"})
    import json
    d = json.loads(out)["daily"][0]
    assert d["tempMax"] == "30"
    assert "cloud" not in d
    assert "wind360Day" not in d


def test_run_tool_unknown():
    out = agent.run_tool("nope", {})
    import json
    assert "未知工具" in json.loads(out)["error"]


def test_run_tool_propagates_error():
    with patch.object(agent, "lookup_city", return_value={"error": "和风接口错误: code=404", "location": []}):
        out = agent.run_tool("get_city", {"query": "x"})
    import json
    assert "error" in json.loads(out)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/test_agent.py -v`
Expected: FAIL(`ModuleNotFoundError: qweather.agent`)

- [ ] **Step 3: 实现 agent.py**

`qweather/agent.py`:
```python
"""
qweather Agent:基于 OpenAI tool calling 的持续聊天天气助手。

工具:
- get_city:城市定位(走城市缓存)
- get_daily_weather:每日天气(走天气缓存)

流程:持续聊天;城市定位多结果/无结果时 AI 向用户确认;拿到天气后给穿衣建议。

@author cy
"""
from __future__ import annotations

import json

from openai import OpenAI

from . import config
from .api import lookup_city, get_daily_weather

# 最大工具调用步数(防死循环)
MAX_STEPS = 6

# 退出指令
QUIT_WORDS = {"q", "quit", "exit", "退出"}

SYSTEM_PROMPT = """你是一个中国生活天气助手。你只能查询中国城市的天气。

## 工作流程
1. 用户提到地名时,调用 get_city 查询(query 用用户原话,不要替换;若用户补充了省/上级行政区,传入 adm)
2. 根据 get_city 返回的 count 与 candidates:
   - count 为 0:基于你的知识猜测用户可能想查的城市(错别字/拼音相近),向用户确认"没找到 X,你是不是想查 Y?"
   - count 为 1:直接用其 id 调 get_daily_weather
   - count 大于 1:列出候选(带省 adm1、市 adm2),请用户补充省份,或直接提供 adcode/完整名称
3. 拿到唯一 location_id 后,调用 get_daily_weather(location_id)
4. 根据天气数据给出穿衣与出行建议(参考下方框架)

## 约束
- 只服务中国城市(工具已限定 range=cn)
- 必须使用用户明确提到的地名,不要擅自替换或猜测后直接查(需先确认)
- 用户提供的省市若不存在,告知并确认拼写
- 当你需要向用户确认信息时,直接回复(不要调用工具),等待用户补充

## 穿衣出行建议参考框架
温度区间基础穿搭:
  ≥30℃:短袖、防晒衣、遮阳帽,注意防晒补水
  20-29℃:短袖/薄长袖
  10-19℃:薄外套、长袖、卫衣
  0-9℃:厚外套、毛衣、风衣
  <0℃:羽绒服、棉衣、围巾手套
附加提醒:紫外线指数(uvIndex)≥6 需强防晒;风力(windScale)≥5 级注意防风;有降水(precip>0)带伞;昼夜温差(tempMax-tempMin)>10℃ 建议洋葱式穿搭
"""

# 工具定义(OpenAI function calling schema)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_city",
            "description": "查询中国城市,返回候选列表。query 用用户原话,adm 为用户补充的省/上级行政区。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "城市名称(用户原话),映射到和风 location 参数",
                    },
                    "adm": {
                        "type": "string",
                        "description": "上级行政区(省/市),用于排除重名,可选",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_weather",
            "description": "根据 location_id 获取每日天气预报(默认 3 天)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "location_id": {
                        "type": "string",
                        "description": "和风 LocationID(来自 get_city 的返回)",
                    },
                    "days": {
                        "type": "string",
                        "description": "预报天数:3d/7d/10d/15d/30d,默认 3d",
                        "enum": ["3d", "7d", "10d", "15d", "30d"],
                    },
                },
                "required": ["location_id"],
            },
        },
    },
]


def run_tool(name: str, args: dict) -> str:
    """
    分发工具调用,返回精简后的 JSON 字符串结果。

    Args:
        name: 工具名 get_city / get_daily_weather
        args: 工具参数

    Returns:
        JSON 字符串,含候选/天气或 error
    """
    if name == "get_city":
        result = lookup_city(args.get("query", ""), args.get("adm", ""))
        candidates = [
            {
                "name": c.get("name"),
                "id": c.get("id"),
                "adm1": c.get("adm1"),
                "adm2": c.get("adm2"),
                "lat": c.get("lat"),
                "lon": c.get("lon"),
                "rank": c.get("rank"),
            }
            for c in result.get("location", [])
        ]
        out = {"count": len(candidates), "candidates": candidates}
        if "error" in result:
            out["error"] = result["error"]
        return json.dumps(out, ensure_ascii=False)

    if name == "get_daily_weather":
        result = get_daily_weather(args.get("location_id", ""), args.get("days", "3d"))
        slim = [
            {
                "fxDate": d.get("fxDate"),
                "tempMax": d.get("tempMax"),
                "tempMin": d.get("tempMin"),
                "textDay": d.get("textDay"),
                "textNight": d.get("textNight"),
                "windScaleDay": d.get("windScaleDay"),
                "windDirDay": d.get("windDirDay"),
                "humidity": d.get("humidity"),
                "precip": d.get("precip"),
                "uvIndex": d.get("uvIndex"),
            }
            for d in result.get("daily", [])
        ]
        out = {"daily": slim}
        if "error" in result:
            out["error"] = result["error"]
        return json.dumps(out, ensure_ascii=False)

    return json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)


def run_chat() -> None:
    """启动持续聊天天气助手。"""
    config.check_config()

    client = OpenAI(
        api_key=config.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("天气助手已启动(输入 q/退出 结束)\n")

    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见!")
            break
        if not user_input:
            continue
        if user_input.lower() in QUIT_WORDS:
            print("再见!")
            break

        messages.append({"role": "user", "content": user_input})

        # 内层工具调用循环
        for step in range(MAX_STEPS):
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                tools=TOOLS,
            )
            msg = resp.choices[0].message

            # 无工具调用 → 本轮结束
            if not msg.tool_calls:
                print(f"助手: {msg.content}\n")
                messages.append({"role": "assistant", "content": msg.content})
                break

            # 处理工具调用
            messages.append(msg)
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                print(f"  [工具] {tc.function.name}({args})")
                result = run_tool(tc.function.name, args)
                messages.append(
                    {"role": "tool", "tool_call_id": tc.id, "content": result}
                )
        else:
            print(f"[警告] 达到最大步数({MAX_STEPS})限制,强制停止本轮\n")
```

补全 `qweather/__init__.py`:
```python
"""qweather 包:和风天气查询工具(基于 OpenAI tool calling)。"""
from .api import lookup_city, get_daily_weather
from .cache import CityCache, WeatherCache
from .agent import run_chat

__all__ = [
    "lookup_city",
    "get_daily_weather",
    "CityCache",
    "WeatherCache",
    "run_chat",
]
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/test_agent.py -v`
Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git add qweather/agent.py qweather/__init__.py tests/test_agent.py
git commit -m "feat(qweather): Agent 工具定义、run_tool 分发与 run_chat 主循环"
```

---

## Task 7: 入口精简 + 端到端验证

**Files:**
- Modify: `01_tool_calling_real.py`(精简为入口)

- [ ] **Step 1: 精简入口**

用以下内容覆盖 `01_tool_calling_real.py`(原开头代码移除,config 统一管配置):
```python
"""天气助手入口。

@author cy
"""
from qweather.agent import run_chat

if __name__ == "__main__":
    run_chat()
```

- [ ] **Step 2: 全量测试**

Run: `uv run pytest -v`
Expected: 全部 passed(config 3 + cache 12 + api 8 + agent 5 = 28 passed)

- [ ] **Step 3: 配置校验手动验证**

确认 `.env` 中 `QWEATHER_KEY` 为和风控制台生成的 JWT token(非占位符),`QWEATHER_HOST`、`DEEPSEEK_API_KEY` 已填。
Run: `uv run 01_tool_calling_real.py`
Expected: 打印"天气助手已启动",进入 `你: ` 提示符。

- [ ] **Step 4: 端到端多轮验证(手动)**

在 `你: ` 依次输入,验证行为:
1. 输入 `朝阳今天天气` → 助手应列出多个候选(北京/辽宁/长春)请用户补充省
2. 输入 `北京的` → 助手定位到北京朝阳区,查天气,给穿衣建议
3. 查看 `.cache/qweather/cities/` 与 `.cache/qweather/weather/` 已生成缓存文件
4. 再次输入 `北京朝阳区天气` → 工具日志显示命中缓存(不重新请求 API)
5. 输入 `q` → 程序退出

- [ ] **Step 5: 提交**

```bash
git add 01_tool_calling_real.py
git commit -m "feat: 精简天气助手入口为调用 qweather.run_chat"
```

---

## Task 8: 测试依赖与 README 收尾

**Files:**
- Modify: `pyproject.toml`(加 pytest 到 dev 依赖,若前序任务已用 uv run pytest 自动装则仅固化)
- Modify: `README.md`(补 qweather 包使用说明)

- [ ] **Step 1: 固化 pytest 为开发依赖**

Run: `uv add --dev pytest`
Expected: `pyproject.toml` 出现 `[dependency-groups] dev = ["pytest>=..."]`(或 equivalent),`uv.lock` 更新。

- [ ] **Step 2: README 补充 qweather 包说明**

在 `README.md` 的「项目结构」补充 `qweather/` 包,并在「快速开始」补"生成 JWT token"步骤与"运行天气助手"命令:
```markdown
### 运行天气助手
1. 生成和风 JWT token:`uv run scripts/gen_qweather_jwt.py`(见 .env.example 配置)
2. 启动助手:`uv run 01_tool_calling_real.py`
```

- [ ] **Step 3: 最终全量测试**

Run: `uv run pytest -v`
Expected: 全部 passed

- [ ] **Step 4: 提交**

```bash
git add pyproject.toml uv.lock README.md
git commit -m "chore: 固化 pytest 开发依赖并更新 README"
```

---

## 验收标准

- [ ] `uv run pytest -v` 全绿(28 项)
- [ ] `uv run 01_tool_calling_real.py` 能持续聊天,城市多轮确认、穿衣建议正常
- [ ] `.cache/qweather/` 缓存正确生成,重复查询命中缓存
- [ ] `01_tool_calling.py` 原样保留未动
- [ ] 缺 `.env` 关键配置时启动报清晰错误并退出
