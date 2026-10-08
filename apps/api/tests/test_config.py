import os

from app.config import Settings


def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-123")
    monkeypatch.setenv("LLM_MODEL", "deepseek-chat")
    s = Settings.from_env()
    assert s.deepseek_api_key == "sk-test-123"
    assert s.llm_model == "deepseek-chat"


def test_settings_defaults():
    # 通过显式构造测试默认值
    s = Settings(deepseek_api_key="", llm_model="deepseek-chat")
    assert s.deepseek_base_url == "https://api.deepseek.com"
