import pytest

from app.agent.loop import AgentEvent, AgentLoop
from app.agent.tools import Tool, ToolRegistry, make_iot_tools
from app.iot.service import MockIoTService
from app.llm.base import LLMResponse, ToolCall
from app.llm.fake import FakeProvider


async def test_happy_path_tool_call_then_answer():
    """LLM 先发工具调用，再给最终答案。"""
    iot = MockIoTService.with_seed_data()
    reg = ToolRegistry()
    for t in make_iot_tools(iot):
        reg.register(t)

    scripted = [
        LLMResponse(
            text=None,
            tool_calls=[ToolCall(id="c1", name="turn_on_light", arguments={"room": "客厅", "on": True})],
            usage={},
        ),
        LLMResponse(text="好的，客厅灯已打开。", tool_calls=[], usage={}),
    ]
    llm = FakeProvider(responses=scripted)
    loop = AgentLoop(llm=llm, registry=reg)

    events = [e async for e in loop.stream("把客厅灯打开")]
    kinds = [e.kind for e in events]
    assert "tool_call" in kinds
    assert "tool_result" in kinds
    assert "text_delta" in kinds or "done" in kinds
    final_text = "".join(e.text or "" for e in events if e.kind == "text_delta")
    assert "客厅灯" in final_text

    # 灯真的开了
    assert iot.get_device("light-living-1").state.on is True


async def test_unknown_tool_yields_error_not_crash():
    """LLM 调用不存在的工具 → tool_result 里返回结构化错误，loop 不崩、LLM 能继续回答用户。"""
    reg = ToolRegistry()
    scripted = [
        LLMResponse(
            text=None,
            tool_calls=[ToolCall(id="c1", name="nonexistent_tool", arguments={})],
            usage={},
        ),
        LLMResponse(text="抱歉，我无法执行该操作。", tool_calls=[], usage={}),
    ]
    loop = AgentLoop(llm=FakeProvider(responses=scripted), registry=reg)
    events = [e async for e in loop.stream("do something")]

    # tool_result 里必须有 unknown tool 错误信息
    tool_results = [e for e in events if e.kind == "tool_result"]
    assert any("unknown tool" in str(e.result) for e in tool_results)

    # 最终 LLM 给出了回答
    final_text = "".join(e.text or "" for e in events if e.kind == "text_delta")
    assert "抱歉" in final_text


async def test_invalid_tool_call_json_yields_clean_error():
    """LLM 返回的 arguments 是非法 JSON → tool_result 里给出清晰诊断（不是神秘 TypeError）。"""
    reg = ToolRegistry()
    reg.register(Tool(
        name="noop",
        description="no-op",
        parameters={"type": "object", "properties": {}},
        handler=lambda: {"ok": True},
    ))
    # 模拟 DeepSeekProvider 的降级路径：非法 JSON 会被塞进 __invalid_json__ 字段
    scripted = [
        LLMResponse(
            text=None,
            tool_calls=[ToolCall(id="c1", name="noop", arguments={"__invalid_json__": "{not valid json"})],
            usage={},
        ),
        LLMResponse(text="工具参数格式不对，让我重试一下。", tool_calls=[], usage={}),
    ]
    llm = FakeProvider(responses=scripted)
    loop = AgentLoop(llm=llm, registry=reg)
    events = [e async for e in loop.stream("do something")]

    tool_results = [e for e in events if e.kind == "tool_result"]
    assert tool_results, "tool_result 事件必须发出"
    # 关键：错误信息必须提及 JSON/参数，不能是 TypeError: unexpected keyword argument
    error_str = str(tool_results[0].result).lower()
    assert "json" in error_str or "invalid" in error_str, f"错误信息不够清晰: {tool_results[0].result}"
    assert "unexpected keyword" not in error_str, "不应把底层 TypeError 直接透给 LLM"

    # LLM 拿到错误后继续推理
    assert len(llm.calls) == 2


async def test_tool_exception_propagates_to_llm_not_loop_crash():
    """工具抛 ValueError → 作为 tool result 回传 LLM，loop 不崩且 LLM 拿到错误后继续推理。"""
    reg = ToolRegistry()

    def boom(room: str, temperature: int) -> dict:
        raise ValueError("temperature out of range")

    reg.register(Tool(
        name="set_temperature",
        description="set temp",
        parameters={"type": "object", "properties": {"room": {"type": "string"}, "temperature": {"type": "integer"}}},
        handler=boom,
    ))
    scripted = [
        LLMResponse(
            text=None,
            tool_calls=[ToolCall(id="c1", name="set_temperature", arguments={"room": "卧室", "temperature": 99})],
            usage={},
        ),
        LLMResponse(text="温度范围不对，需要 16-30 度。", tool_calls=[], usage={}),
    ]
    llm = FakeProvider(responses=scripted)
    loop = AgentLoop(llm=llm, registry=reg)
    events = [e async for e in loop.stream("把卧室调到 99 度")]

    # tool_result 事件里的 content 应包含错误信息
    tool_results = [e for e in events if e.kind == "tool_result"]
    assert any("temperature" in str(e.result) for e in tool_results)

    # 关键：LLM 被再次调用（第二次），并且消息历史里带上了 tool 错误
    assert len(llm.calls) == 2, "loop 应在 tool_result 后再次调用 LLM"
    second_call_messages = llm.calls[1][0]
    tool_msgs = [m for m in second_call_messages if m.get("role") == "tool"]
    assert tool_msgs, "第二次 LLM 调用必须带 role=tool 的消息"
    assert "temperature" in tool_msgs[0]["content"]

    # 最终 LLM 给出了针对错误的回答
    final_text = "".join(e.text or "" for e in events if e.kind == "text_delta")
    assert "温度" in final_text


async def test_max_iterations_prevents_infinite_loop():
    """LLM 每次都发 tool call、永不返回最终答案 → max_iterations 触发 error 事件。"""
    reg = ToolRegistry()
    reg.register(Tool(
        name="noop",
        description="no-op",
        parameters={"type": "object", "properties": {}},
        handler=lambda: {"ok": True},
    ))

    def endless():
        while True:
            yield LLMResponse(
                text=None,
                tool_calls=[ToolCall(id="c", name="noop", arguments={})],
                usage={},
            )

    class EndlessProvider:
        def __init__(self):
            self._gen = endless()

        async def complete(self, messages, tools):
            return next(self._gen)

    loop = AgentLoop(llm=EndlessProvider(), registry=reg, max_iterations=3)
    events = [e async for e in loop.stream("loop forever")]
    errors = [e for e in events if e.kind == "error"]
    assert any("max" in str(e.message).lower() or "iteration" in str(e.message).lower() for e in errors)


async def test_history_is_passed_to_llm():
    reg = ToolRegistry()
    scripted = [LLMResponse(text="ok", tool_calls=[], usage={})]
    llm = FakeProvider(responses=scripted)
    loop = AgentLoop(llm=llm, registry=reg)
    history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    _ = [e async for e in loop.stream("next", history=history)]
    # FakeProvider.calls 记录了每次 complete 的入参
    first_messages = llm.calls[0][0]
    assert first_messages[0]["content"] == "hi"
    assert first_messages[1]["content"] == "hello"
