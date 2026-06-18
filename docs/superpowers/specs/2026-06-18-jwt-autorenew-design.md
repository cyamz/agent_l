# JWT 自动续期与密钥管理设计(WIP)

> 创建:2026-06-18
> 状态:**WIP** — 三段设计已呈现,第 1、2 段已确认,第 3 段待最终确认;尚未 spec review 与实现

## 背景

当前 `qweather` 的 JWT token 存在 `.env` 的 `QWEATHER_KEY`,和风 JWT 最长 24 小时过期,需手动重签 + 改 `.env`。本次改进:token 自动管理(缓存 + 过期自动重签),pem 密钥放专门资源目录,路径在代码里写死(约定优于配置)。

## 目标

- token 不写 `.env`,改由 `qweather/auth.py` 缓存到 `.cache/qweather/token.json` 并自动重签
- 重签时机:**启动检查 + 请求遇 401 自动重签重试**(最稳)
- pem 密钥放 `resources/qweather/`,路径在代码写死(`config.py` 常量,相对项目根)
- 生成 `ed25519-private.pem.example` / `ed25519-public.pem.example`(占位,可提交)
- 敏感信息(真实 pem、token、.env)不进 git

## 设计

### 第 1 段:qweather/auth.py(token 自动管理)

新模块 `qweather/auth.py`,封装 token 生命周期:

| 方法 | 职责 |
|------|------|
| `get_token()` | 返回有效 token:读缓存有效就用,过期/无则 `renew()` |
| `renew()` | 强制重签:读私钥 + PROJECT_ID/CREDENTIAL_ID → 签 → 写缓存 |
| `ensure_token()` | 启动用,等价 `get_token()` |

**token 缓存**:
- 路径:`.cache/qweather/token.json`(已 gitignore)
- 内容:`{"token": "eyJ...", "exp": 1781859014}`
- 过期判断:`exp - now <= 300`(5 分钟缓冲)视为过期
- 读写:auth 自管简单 JSON 读写(文件损坏当未命中,重签)

**签名逻辑迁移**:`gen_qweather_jwt.py` 的 `generate_token(project_id, credential_id, private_key_pem, ttl)` 迁到 `auth.py`(包内复用);`gen_qweather_jwt.py` 改为 CLI 包装(`from qweather.auth import renew`)。

### 第 2 段:pem 资源目录 + 路径写死

**pem 位置** `resources/qweather/`:
```
resources/qweather/
├── ed25519-private.pem            # 真实私钥(gitignore)
├── ed25519-public.pem             # 真实公钥(gitignore)
├── ed25519-private.pem.example    # 私钥占位(可提交)
└── ed25519-public.pem.example     # 公钥占位(可提交)
```

**路径写死**(`config.py`):
```python
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
QWEATHER_PRIVATE_KEY_PATH = _PROJECT_ROOT / "resources" / "qweather" / "ed25519-private.pem"
```

**`.env` 精简**(移除两项):
- ❌ `QWEATHER_KEY`(token 自动)
- ❌ `QWEATHER_PRIVATE_KEY_FILE`(路径写死)

保留:`DEEPSEEK_API_KEY`、`QWEATHER_HOST`、`QWEATHER_PROJECT_ID`、`QWEATHER_CREDENTIAL_ID`

**`config.py` 调整**:
- 加 `QWEATHER_PRIVATE_KEY_PATH` 常量
- 删 `QWEATHER_KEY` 常量
- `check_config()` 校验:DEEPSEEK_API_KEY、QWEATHER_HOST、QWEATHER_PROJECT_ID、QWEATHER_CREDENTIAL_ID、**私钥文件存在**(`QWEATHER_PRIVATE_KEY_PATH.is_file()`)

**`.gitignore`**:无需新增(`*.pem` 忽略真实密钥含 `resources/qweather/*.pem`;`.pem.example` 不匹配可提交)

### 第 3 段:模块改动 + 测试

**`api.py` 改动**:
- `_headers()`:`return {"Authorization": f"Bearer {auth.get_token()}"}`
- 新增 `_request(url, params)` 带 401 重试:
```python
def _request(url, params):
    resp = httpx.get(url, params=params, headers=_headers(), timeout=10)
    if resp.status_code == 401:
        auth.renew()
        resp = httpx.get(url, params=params, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()
```
- `lookup_city`/`get_daily_weather` 用 `_request(...)`

**`agent.py` 改动**:`run_chat()` 启动顺序 `config.check_config()` → `auth.ensure_token()` → 创建 client → 聊天循环

**`scripts/gen_qweather_jwt.py` 改动**:`generate_token` 迁走,脚本变 CLI 包装(`from qweather.auth import renew` → `renew()` → 打印 token)

**测试**:
| 文件 | 测试点 |
|------|--------|
| `tests/test_auth.py`(新) | `generate_token` 签出可解码 JWT;`get_token` 缓存命中;过期触发 `renew`(mock);`renew` 写 token.json;缓冲边界 |
| `tests/test_api.py`(改) | 401 重试(mock 第一次 401 第二次 200);401 重试仍 401 → error |
| `tests/test_config.py`(改) | 私钥文件存在校验(tmp_path + monkeypatch) |

## 完整数据流
```
run_chat() → config.check_config() → auth.ensure_token() [首次签/读缓存]
  → 聊天循环
       api.lookup_city → _request → _headers[auth.get_token()]
                                       ↓ 401
                                     auth.renew() → 重试 1 次
```

## 当前状态
- [x] 第 1 段(auth.py token 管理)— 已确认
- [x] 第 2 段(pem 资源目录 + 路径写死)— 已确认
- [ ] 第 3 段(模块改动 + 测试)— 已呈现,待最终确认
- [ ] spec review
- [ ] 实现(转 writing-plans)
