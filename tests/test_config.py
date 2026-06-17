"""config 模块测试。"""


def _reload_config(monkeypatch, env):
    """用指定 env 重新加载 config(不读真实 .env)。"""
    import qweather.config as config
    for k in ["DEEPSEEK_API_KEY", "QWEATHER_HOST", "QWEATHER_KEY"]:
        monkeypatch.delenv(k, raising=False)
    # 屏蔽真实 .env,只用 monkeypatch 注入的测试值
    monkeypatch.setattr(config, "load_dotenv", lambda *a, **k: None)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    config.load()
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
