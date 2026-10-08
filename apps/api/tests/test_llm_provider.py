import pytest

from app.config import Settings
from app.llm.base import LLMResponse, ToolCall
from app.llm.deepseek import DeepSeekProvider
from app.llm.fake import FakeProvider


async def test_fake_provider_returns_scripted_response():
    scripted = LLMResponse(text="你好", tool_calls=[], usage={"total_tokens": 10})
    p = FakeProvider(responses=[scripted])
    resp = await p.complete(messages=[{"role": "user", "content": "hi"}], tools=[])
    assert resp.text == "你好"
    assert resp.tool_calls == []


async def test_fake_provider_yields_tool_calls():
    scripted = LLMResponse(
        text=None,
        tool_calls=[ToolCall(id="call-1", name="turn_on_light", arguments={"room": "客厅"})],
        usage={"total_tokens": 5},
    )
    p = FakeProvider(responses=[scripted])
    resp = await p.complete(messages=[], tools=[{"type": "function", "function": {"name": "turn_on_light"}}])
    assert resp.tool_calls[0].name == "turn_on_light"
    assert resp.tool_calls[0].arguments == {"room": "客厅"}


async def test_fake_provider_pops_in_order():
    r1 = LLMResponse(text="first", tool_calls=[], usage={})
    r2 = LLMResponse(text="second", tool_calls=[], usage={})
    p = FakeProvider(responses=[r1, r2])
    assert (await p.complete(messages=[], tools=[])).text == "first"
    assert (await p.complete(messages=[], tools=[])).text == "second"


def test_deepseek_requires_api_key():
    s = Settings(deepseek_api_key="")
    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        DeepSeekProvider(settings=s)


def test_deepseek_accepts_valid_settings():
    s = Settings(deepseek_api_key="sk-test-123")
    p = DeepSeekProvider(settings=s)
    assert p.model == s.llm_model
