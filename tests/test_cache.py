"""cache 模块测试。"""
from pathlib import Path

from qweather.cache import _safe_filename, CityCache


def test_safe_filename_short_replaces_pipe():
    # | 是 Windows 非法字符,必须被替换
    name = _safe_filename("朝阳|北京|cn")
    assert "|" not in name
    assert "朝阳" in name and "北京" in name and "cn" in name


def test_safe_filename_strips_illegal_chars():
    name = _safe_filename('a/b\\c d|e:f*g?h"i<j>k')
    for ch in '/\\:*?"<>| ':
        assert ch not in name


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
