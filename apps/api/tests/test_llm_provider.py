import pytest

from app.config import Settings
from app.llm.anthropic import AnthropicProvider
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


def test_anthropic_requires_api_key():
    s = Settings(anthropic_api_key="")
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        AnthropicProvider(settings=s)


def test_anthropic_accepts_valid_settings():
    s = Settings(anthropic_api_key="sk-ant-test", anthropic_model="xiaomi/mimo-v2.6-pro")
    p = AnthropicProvider(settings=s)
    assert p.model == "xiaomi/mimo-v2.6-pro"


def test_anthropic_converts_openai_tools_to_anthropic_format():
    """OpenAI function-calling schema → Anthropic tool schema 的转换。"""
    s = Settings(anthropic_api_key="sk-ant-test")
    p = AnthropicProvider(settings=s)
    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": "turn_on_light",
                "description": "Turn on lights",
                "parameters": {
                    "type": "object",
                    "properties": {"room": {"type": "string"}},
                    "required": ["room"],
                },
            },
        }
    ]
    anthropic_tools = p._to_anthropic_tools(openai_tools)
    assert anthropic_tools[0]["name"] == "turn_on_light"
    assert anthropic_tools[0]["description"] == "Turn on lights"
    assert anthropic_tools[0]["input_schema"]["type"] == "object"
    assert "room" in anthropic_tools[0]["input_schema"]["properties"]


def test_anthropic_parses_tool_use_blocks():
    """Anthropic tool_use content block → LLMResponse.tool_calls。"""
    s = Settings(anthropic_api_key="sk-ant-test")
    p = AnthropicProvider(settings=s)

    class FakeToolUse:
        type = "tool_use"
        id = "toolu_123"
        name = "turn_on_light"
        input = {"room": "客厅"}

    class FakeTextBlock:
        type = "text"
        text = "好的"

    class FakeStopResponse:
        stop_reason = "tool_use"
        content = [FakeTextBlock(), FakeToolUse()]

        class Usage:
            input_tokens = 10
            output_tokens = 5

        usage = Usage()

    resp = p._to_llm_response(FakeStopResponse())
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].name == "turn_on_light"
    assert resp.tool_calls[0].arguments == {"room": "客厅"}
    assert resp.usage["prompt_tokens"] == 10
    assert resp.usage["completion_tokens"] == 5
