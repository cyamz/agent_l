# 和风天气工具设计(基于 OpenAI tool calling)

> 创建日期:2026-06-17
> 状态:已确认,待实现

## 概述

基于 OpenAI SDK(调用 DeepSeek)与和风天气(qweather)接口,实现一个简易的天气查询工具。采用 **AI Agent(tool calling)模式**,持续聊天交互。AI 通过工具调用完成"城市定位 → 查询天气 → 给穿衣出行建议"全流程,其中:

- 城市定位支持多轮确认(重名、错别字、不存在等情况)
- 缓存层缓存城市信息与当日天气,查询先走缓存
- 穿衣出行建议由 AI 结合实时天气与 prompt 框架自由生成

接口文档见 `docs/qweather_api/`:
- 城市搜索:`city-lookup.md` → `GET /geo/v2/city/lookup`
- 每日预报:`weather-daily-forecast.md` → `GET /v7/weather/{days}`

## 目标与非目标

**目标**
- tool calling 持续聊天,能连续查询多个城市
- 城市定位唯一化:多结果/无结果/错别字时,AI 多轮确认到唯一 `location_id`
- 仅服务中国城市(`range=cn`)
- 两类缓存(城市、当日天气),被多个 py 共享复用
- 穿衣出行建议:AI 自由发挥 + prompt 参考框架
- 包结构,便于后期扩展天气相关功能

**非目标**
- 不做单独的规则型穿衣工具(避免 if-else 死板建议)
- 不做并发/文件锁(简易工具)
- 不做 HTTP 自动重试
- 不覆盖和风全部接口(仅城市搜索 + 每日预报)

## 架构(包结构)

```
agent/                          # 项目根(现有)
├── qweather/                   # 和风天气包(新建)
│   ├── __init__.py             # 再导出公共接口
│   ├── config.py               # 集中读取 .env 配置 + 启动校验
│   ├── cache.py                # 缓存读写:CityCache + WeatherCache
│   ├── api.py                  # HTTP 封装:lookup_city()、get_daily_weather(),内部走缓存
│   └── agent.py                # OpenAI client + 工具定义 + 持续聊天主循环 run_chat()
├── 01_tool_calling.py          # 原 tool calling 示例(保留不动)
├── 01_tool_calling_real.py     # 入口(精简):from qweather.agent import run_chat
├── pyproject.toml              # 显式新增 httpx 依赖
├── .env / .env.example         # 已有
└── .gitignore                  # 追加 .cache/
```

后期扩展示例:加空气质量 → `api.py` 增 `get_air_quality()`,`cache.py` 增对应缓存,agent 加工具,互不干扰。

## 模块职责

| 模块 | 职责 | 对外接口 |
|------|------|----------|
| `config.py` | 读 env,启动校验必填项 | `QWEATHER_KEY`、`QWEATHER_HOST`、`DEEPSEEK_API_KEY` |
| `cache.py` | 两类缓存 load/save/查过期,不关心业务 | `CityCache`、`WeatherCache` |
| `api.py` | 封装和风两个接口 HTTP,自动走缓存 | `lookup_city(query, adm)`、`get_daily_weather(location_id, days)` |
| `agent.py` | 工具定义、Agent 主循环、system prompt | `run_chat()` |
| `__init__.py` | 再导出,保持 import 简洁 | — |

入口 `01_tool_calling_real.py` 精简为:
```python
from qweather.agent import run_chat

if __name__ == "__main__":
    run_chat()
```

## 缓存设计

目录结构(项目级缓存根,按包/服务分层):
```
.cache/
└── qweather/
    ├── cities/{query_key}.json              # 城市信息
    └── weather/{location_id}/{yyyy-mm-dd}.json  # 某地某日天气
```

### 城市缓存(CityCache)
- **key**:由查询参数拼成 `{location}|{adm}|cn`(`range` 固定 `cn`),文件名做安全转义(去空格/斜杠)+ 必要时短哈希
- **value**:city-lookup 完整响应(`location[]` 数组)+ 写入时间戳
- **过期**:地理位置基本不变 → **长期缓存,不主动过期**(同 key 命中即返回;需刷新手动删文件)
- **命中逻辑**:`lookup_city(query, adm)` 先按 key 读文件,命中返回,未命中请求 API 并写入

### 当日天气缓存(WeatherCache)
- **key**:`{location_id}/{日期}`,按天一个文件
- **value**:`daily[]` 中对应 `fxDate` 的那条 + 时间戳
- **过期**:**当天有效**。查询时 `weather/{location_id}/{today}.json` 存在即命中;跨天自然失效
- **写入**:`get_daily_weather` 请求 API 后,把返回 `daily[]` **按每个 `fxDate` 拆分**存储(这样 `3d`/`7d` 请求能共享同一天缓存)
- **命中逻辑**:查询时先检查所需日期是否都在缓存,命中组装返回,缺失则请求 API 刷新

### 格式与并发
- 纯 JSON 文件,`json.dump(ensure_ascii=False, indent=2)`
- 简易工具不加文件锁

复用方式:`from qweather.api import lookup_city, get_daily_weather` 拿带缓存数据;`from qweather.cache import CityCache, WeatherCache` 手动清缓存。

## 工具定义(两个,都带缓存,AI 不感知缓存)

### 工具 1 `get_city`
- 参数:`query`(用户原话/地名)、`adm`(可选,补充的省/上级行政区)
- 内部:`lookup_city(query, adm)`(range 固定 `cn`)走城市缓存
- 返回给 AI:结构化候选列表 `[{name, id, adm1, adm2, lat, lon, rank}, ...]`;无结果返回空列表

### 工具 2 `get_daily_weather`
- 参数:`location_id`(来自 get_city 的 `id`)、`days`(默认 `3d`)
- 内部:`get_daily_weather(location_id, days)` 走天气缓存(按 fxDate 拆分)
- 返回给 AI:当日及后续几天的温度、天气状况、风、湿度、降水、紫外线等关键字段

## Agent 主循环

延续 `01_tool_calling.py` 循环模式,改为持续聊天(伪代码):
```
messages = [system_prompt]
while True:
    user_input = input("你: ")
    若是退出指令(q/quit/退出) → break
    messages.append(user)
    for step in range(max_steps=6):           # 内层工具调用循环
        resp = client.chat.completions.create(model, messages, tools)
        msg = resp.choices[0].message
        if 无 tool_calls → 打印 msg.content; break   # 本轮结束,回外层等下次输入
        messages.append(msg)
        for tc in msg.tool_calls:
            result = 分发到 get_city / get_daily_weather
            messages.append(tool 结果)
```

**多轮确认机制**:AI 需要向用户确认时(多结果/无结果),本轮**不带 tool_calls 直接回复** → 自然回外层 `input()` 等用户补充 → 下一轮 AI 带新参数再调 `get_city`。

## 城市确认 AI 行为(system prompt)

| 情况 | AI 行为 |
|------|---------|
| 用户输入地名,首次查询 | 调 `get_city(query=用户原话)` |
| 返回 **0 结果** | 基于知识猜测(错别字/拼音相近),向用户确认"没找到 X,是不是想查 Y?" |
| 返回 **1 结果** | 直接取该 `id` 进入查天气 |
| 返回 **多结果**(如"朝阳") | 列出候选(带省 `adm1`/市 `adm2`),请用户补充省份或提供 adcode/具体全称 |
| 用户补充后 | 用 `adm` 参数再调 `get_city` 缩小范围 |
| 不存在的省市 | 告知并确认拼写 |
| 拿到唯一 `location_id` 后 | 调 `get_daily_weather(location_id)` → 基于结果给穿衣/出行建议 |

system prompt 另约束:**只服务中国城市**(工具已 `range=cn`),**必须用用户明确提到的地名,不擅自替换**。

## 穿衣出行建议

**方式:AI 自由发挥 + system prompt 参考框架**(不做单独工具)。

理由:穿衣建议是多维度综合判断(温度+体感+风+湿度+紫外+昼夜温差),规则型工具(如现有 `search_clothes` 只看温度)效果差;AI 综合判断是其强项;prompt 框架保证底线一致性。

system prompt 嵌入参考框架:
```
温度区间基础穿搭:
  ≥30℃:短袖、防晒衣、遮阳帽,注意防晒补水
  20-29℃:短袖/薄长袖
  10-19℃:薄外套、长袖、卫衣
  0-9℃:厚外套、毛衣、风衣
  <0℃:羽绒服、棉衣、围巾手套
附加提醒:紫外线指数≥6需强防晒;风力≥5级注意防风;有降水带伞;昼夜温差>10℃建议洋葱式穿搭
```

AI 拿到 `get_daily_weather` 结果后,据此框架结合实时天气生成具体建议。

## 错误处理

| 层 | 处理 |
|----|------|
| **HTTP 层**(`api.py`) | 捕获 `httpx` 网络异常(超时/连接失败),不重试,返回 `{"error": "网络请求失败:..."}` |
| **业务层**(`api.py`) | 和风 `code != "200"`,返回 `{"error": "和风接口错误: code=xxx"}` |
| **工具层**(`agent.py`) | 工具结果统一 JSON 字符串;含 `error` 时 AI 自然向用户解释 |
| **缓存层**(`cache.py`) | 文件损坏/读写异常 → **静默降级**(当未命中,回退请求 API),不阻断主流程 |
| **循环保护** | `max_steps=6`,超出打印"达到最大步数,强制停止本轮",回外层等下一次输入 |

## 配置校验

`config.py` 模块加载时读 env。`run_chat()` 启动时检查 `QWEATHER_KEY` / `QWEATHER_HOST` / `DEEPSEEK_API_KEY` 是否存在且非占位符(`your_xxx_here`),缺失则打印清晰提示并退出:
```
缺少配置:QWEATHER_KEY 未设置。请在 .env 配置(参考 .env.example)
```

## 数据流示例("朝阳今天天气")

```
用户:"朝阳今天天气"
→ AI 调 get_city(query="朝阳")            [查 .cache/qweather/cities/,未命中→请求API→写入]
→ 返回 3 个候选(北京朝阳/辽宁朝阳/长春朝阳)
→ AI 无 tool_calls,直接回复列候选请用户选省  → 回到 input()
用户:"北京的"
→ AI 调 get_city(query="朝阳", adm="北京")   [缓存命中或再请求]
→ 返回 1 个(id=101010300)
→ AI 调 get_daily_weather("101010300","3d")  [查天气缓存,未命中→请求→按fxDate写入]
→ AI 拿到天气,结合 prompt 穿衣框架给:"北京朝阳区今天 18℃,多云…建议薄外套…"
```

## 测试策略(不强制 TDD,提供关键单测)

- `cache.py`:过期判断/读写(纯文件逻辑,最值得测)
- `api.py`:响应解析(mock httpx)
- 工具的缓存命中/未命中分支

## 依赖与配置变更

- `pyproject.toml`:显式新增 `httpx`
- `.gitignore`:追加 `.cache/`
- 运行:`uv run 01_tool_calling_real.py`,持续聊天,输入 `q`/`退出`/`quit` 结束

## 现有代码处理

- `01_tool_calling.py`:原样保留,完全不动(学习示例)
- `01_tool_calling_real.py`:精简为入口(用户已确认可调整)
