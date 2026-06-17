# Agent

## 简介

基于 Python 的 AI Agent 实验项目，使用 OpenAI SDK 调用 DeepSeek 大模型，演示了工具调用（Tool Calling）的能力。当前包含一个生活助手示例：能够查询城市天气并根据气温给出穿衣建议。

## 技术栈

- **语言**：Python >= 3.10
- **包管理**：[uv](https://github.com/astral-sh/uv)（极速 Python 包管理器）
- **大模型 SDK**：openai（通过 DeepSeek 兼容接口调用）
- **其他依赖**：anthropic、langchain-anthropic、langgraph、python-dotenv

## 项目结构

```
.
├── 01_tool_calling.py   # 工具调用示例（天气查询 + 穿衣建议）
├── main.py              # 入口占位文件
├── pyproject.toml       # 项目配置与依赖声明
├── uv.lock              # 依赖锁定文件
├── .env.example         # 环境变量示例（安全，可提交）
├── .env                 # 本地环境变量（已忽略，需自行创建）
├── .gitignore
└── .python-version      # Python 版本声明
```

## 快速开始

### 环境要求

- Windows / macOS / Linux
- Python >= 3.10
- [uv](https://docs.astral.sh/uv/) 包管理器
- DeepSeek API Key（必需）、和风天气 API Key（可选）

### 1. 安装 uv

**Windows（PowerShell）：**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**其他方式：**

```bash
# winget
winget install astral-sh.uv

# scoop
scoop install uv

# pip
pip install uv
```

安装完成后验证：

```bash
uv --version
```

### 2. 克隆项目

```bash
git clone git@github.com:cyamz/agent_l.git
cd agent_l
```

### 3. 配置环境变量

复制示例文件并填写真实密钥：

```bash
cp .env.example .env
```

然后编辑 `.env`，将占位符替换为真实的 API Key：

```
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
QWEATHER_KEY=your_real_qweather_key
QWEATHER_HOST=your_real_qweather_host
```

### 4. 安装依赖

uv 会根据 `pyproject.toml` 和 `uv.lock` 自动创建虚拟环境并安装全部依赖：

```bash
uv sync
```

### 5. 运行

```bash
# 运行工具调用示例（天气查询 + 穿衣建议）
uv run 01_tool_calling.py

# 运行入口占位文件
uv run main.py
```

## uv 常用命令

```bash
uv init                # 初始化一个新的 Python 项目
uv add <package>       # 添加依赖
uv remove <package>    # 移除依赖
uv sync                # 按 lock 文件同步依赖
uv run <script.py>     # 在项目环境中运行脚本
uv venv                # 创建虚拟环境
uv lock                # 更新依赖锁定文件
```

## 常见问题

**Q: 运行时报 `uv: command not found`？**
A: uv 未安装或未配置到 PATH。请先按上方「安装 uv」步骤完成安装；若已安装，重启终端，或手动将 uv 安装目录加入系统环境变量。

**Q: 运行时报 API Key 相关错误？**
A: 检查 `.env` 是否创建、Key 是否填写正确（注意不要填入示例占位符 `your_xxx_here`）。

**Q: 提交时出现 `LF will be replaced by CRLF` 警告？**
A: Windows 下的正常提示，不影响运行。如需统一换行符可自行配置 `.gitattributes`。

## 许可证

MIT
