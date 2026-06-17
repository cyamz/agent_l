"""
qweather 配置模块:集中读取 .env 并提供启动校验。

@author cy
"""
import os
import sys
from dotenv import load_dotenv

# 和风天气配置
QWEATHER_HOST = ""
QWEATHER_KEY = ""

# DeepSeek 配置
DEEPSEEK_API_KEY = ""

# .env.example 中的占位符集合(用于检测未配置)
_PLACEHOLDERS = {
    "your_deepseek_api_key_here",
    "your_qweather_host_here",
    "your_qweather_jwt_token_here",
    "your_project_id_here",
    "your_credential_id_here",
    "path/to/your_ed25519.pem",
}


def load() -> None:
    """从 .env 与环境变量加载配置(模块加载时调用一次,测试可重复调用注入)。"""
    global QWEATHER_HOST, QWEATHER_KEY, DEEPSEEK_API_KEY
    load_dotenv()
    QWEATHER_HOST = os.getenv("QWEATHER_HOST", "")
    QWEATHER_KEY = os.getenv("QWEATHER_KEY", "")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")


def _is_placeholder(value: str) -> bool:
    """判断值是否仍是 .env.example 里的占位符。"""
    return value in _PLACEHOLDERS or value.startswith("your_") or value.endswith("_here")


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


# 模块加载时执行一次
load()
