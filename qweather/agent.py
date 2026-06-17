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
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                print(f"  [工具] {tc.function.name}({args})")
                result = run_tool(tc.function.name, args)
                messages.append(
                    {"role": "tool", "tool_call_id": tc.id, "content": result}
                )
        else:
            print(f"[警告] 达到最大步数({MAX_STEPS})限制,强制停止本轮\n")
