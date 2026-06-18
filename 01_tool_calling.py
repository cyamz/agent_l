from openai import OpenAI
from dotenv import load_dotenv
import os
import json

load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# ---- 定义多个工具 ----
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取某个城市当前的天气情况",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称，必须是用户明确提到的城市，不要猜测"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_clothes",
            "description": "根据气温推荐穿衣建议",
            "parameters": {
                "type": "object",
                "properties": {
                    "temperature": {"type": "number", "description": "当前气温，单位摄氏度"}
                },
                "required": ["temperature"]
            }
        }
    }
]

# ---- 模拟工具的真实执行逻辑 ----
def get_weather(city: str) -> str:
    # 这里先写死数据，模拟真实 API 返回
    fake_data = {
        "北京": 18,
        "上海": 22,
        "宿迁": 25,
    }
    temp = fake_data.get(city, 20)
    return json.dumps({"city": city, "temperature": temp, "condition": "晴"}, ensure_ascii=False)

def search_clothes(temperature: float) -> str:
    if temperature < 10:
        return "建议穿羽绒服或厚外套"
    elif temperature < 20:
        return "建议穿薄外套或长袖"
    else:
        return "建议穿短袖，注意防晒"

def run_tool(name: str, inputs: dict) -> str:
    if name == "get_weather":
        return get_weather(**inputs)
    elif name == "search_clothes":
        return search_clothes(**inputs)
    return "未知工具"

# ---- Agent 主循环 ----
def run_agent(user_input: str):
    messages = [
        {
            "role": "system",
            "content": "你是一个生活助手。当用户提到具体城市时才查询该城市天气，不要猜测或替换用户提到的城市。"
        },
        {"role": "user", "content": user_input}
    ]

    max_steps = 5  # 防止无限循环，生产环境必须设置这个保护
    for step in range(max_steps):
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools
        )

        message = response.choices[0].message

        if not message.tool_calls:
            print(f"\n[最终回答]\n{message.content}")
            return

        print(message)
        messages.append(message)

        for tool_call in message.tool_calls:
            inputs = json.loads(tool_call.function.arguments)
            result = run_tool(tool_call.function.name, inputs)
            print(f"[第{step+1}步 工具调用] {tool_call.function.name}({inputs}) -> {result}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

    print("\n[警告] 达到最大步数限制，强制停止")

if __name__ == "__main__":
    run_agent("北京今天天气怎么样，我该穿什么？")