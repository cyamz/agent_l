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
