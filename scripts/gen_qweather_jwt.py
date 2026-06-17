"""
和风天气 JWT 生成脚本

在和风控制台(https://console.qweather.com)「设置 → 凭证」页面获取:
- Project ID(项目 ID)
- Credential ID(凭证 ID)
- Key(Ed25519 私钥,PEM 格式,保存为 .pem 文件)

配置 .env 后运行:
    uv run scripts/gen_qweather_jwt.py

生成的 token 填入 .env 的 QWEATHER_KEY,供 qweather 包鉴权使用。

@author cy
"""
import os
import sys
import time

import jwt
from dotenv import load_dotenv

load_dotenv()

# 默认 token 有效期:30 天
DEFAULT_TTL = 86400 * 30


def generate_token(project_id: str, credential_id: str, private_key_pem: str,
                   ttl_seconds: int = DEFAULT_TTL) -> str:
    """
    签发和风天气 JWT

    Args:
        project_id: 项目 ID,对应 JWT payload 的 sub
        credential_id: 凭证 ID,对应 JWT header 的 kid
        private_key_pem: Ed25519 私钥(PEM 格式字符串)
        ttl_seconds: token 有效期(秒),默认 30 天

    Returns:
        签发的 JWT 字符串
    """
    now = int(time.time())
    payload = {
        "sub": project_id,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    headers = {"kid": credential_id}
    return jwt.encode(payload, private_key_pem, algorithm="EdDSA", headers=headers)


def main():
    project_id = os.getenv("QWEATHER_PROJECT_ID")
    credential_id = os.getenv("QWEATHER_CREDENTIAL_ID")
    key_file = os.getenv("QWEATHER_PRIVATE_KEY_FILE")

    # 校验配置完整性
    missing = []
    if not project_id:
        missing.append("QWEATHER_PROJECT_ID")
    if not credential_id:
        missing.append("QWEATHER_CREDENTIAL_ID")
    if not key_file:
        missing.append("QWEATHER_PRIVATE_KEY_FILE")
    if missing:
        print(f"[错误] .env 缺少配置:{', '.join(missing)}")
        print("请在和风控制台「设置 → 凭证」获取,并填入 .env(参考 .env.example)")
        sys.exit(1)

    if not os.path.isfile(key_file):
        print(f"[错误] 私钥文件不存在:{key_file}")
        print("请将控制台的 Key(PEM 格式 Ed25519 私钥)保存为该文件")
        sys.exit(1)

    with open(key_file, "r", encoding="utf-8") as f:
        private_key_pem = f.read()

    token = generate_token(project_id, credential_id, private_key_pem)
    print("[生成成功] 和风天气 JWT(有效期 30 天):\n")
    print(token)
    print("\n将上面这段 token 完整填入 .env 的 QWEATHER_KEY 即可。")


if __name__ == "__main__":
    main()
