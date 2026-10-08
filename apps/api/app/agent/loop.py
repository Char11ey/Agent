import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from app.agent.tools import ToolRegistry
from app.llm.base import LLMProvider, LLMResponse, ToolCall


@dataclass
class AgentEvent:
    kind: str  # "tool_call" | "tool_result" | "text_delta" | "error" | "done"
    # tool_call
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None
    # tool_result
    result: Any = None
    # text_delta
    text: str | None = None
    # error
    message: str | None = None
    # done
    usage: dict[str, int] = field(default_factory=dict)


class AgentLoop:
    def __init__(
        self,
        llm: LLMProvider,
        registry: ToolRegistry,
        max_iterations: int = 6,
    ) -> None:
        self.llm = llm
        self.registry = registry
        self.max_iterations = max_iterations

    async def stream(
        self,
        user_message: str,
        history: list[dict] | None = None,
    ) -> AsyncIterator[AgentEvent]:
        messages: list[dict] = list(history or [])
        messages.append({"role": "user", "content": user_message})
        tools_schema = self.registry.openai_schemas()

        for _ in range(self.max_iterations):
            response: LLMResponse = await self.llm.complete(messages=messages, tools=tools_schema)

            # 情况 1：模型给了最终答案
            if not response.tool_calls:
                if response.text:
                    yield AgentEvent(kind="text_delta", text=response.text)
                yield AgentEvent(kind="done", usage=response.usage)
                return

            # 情况 2：模型发了工具调用
            # 先把 assistant 的 tool_calls 塞回历史
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": response.text}
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                    },
                }
                for tc in response.tool_calls
            ]
            messages.append(assistant_msg)

            for tc in response.tool_calls:
                yield AgentEvent(
                    kind="tool_call",
                    tool_call_id=tc.id,
                    tool_name=tc.name,
                    tool_arguments=tc.arguments,
                )
                result = self._execute_tool(tc)
                yield AgentEvent(
                    kind="tool_result",
                    tool_call_id=tc.id,
                    tool_name=tc.name,
                    result=result,
                )
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })

        # 走完 max_iterations 仍未拿到最终答案 → 报错并终止
        yield AgentEvent(
            kind="error",
            message=f"Agent exceeded max_iterations ({self.max_iterations}) without producing a final answer.",
        )
        yield AgentEvent(kind="done", usage={})

    def _execute_tool(self, tc: ToolCall) -> Any:
        """执行工具。工具抛异常或不存在 → 返回错误 dict，供 LLM 继续推理。"""
        # DeepSeekProvider 在 arguments 非法 JSON 时会塞进 __invalid_json__ 字段；
        # 这里先于 handler 执行拦截，给 LLM 一个可读的诊断而不是底层 TypeError。
        if "__invalid_json__" in tc.arguments:
            raw = tc.arguments["__invalid_json__"]
            return {
                "ok": False,
                "error": (
                    f"invalid JSON in tool arguments for '{tc.name}': "
                    f"model returned non-JSON arguments: {raw!r}. "
                    "Please retry with a valid JSON object."
                ),
            }
        try:
            tool = self.registry.get(tc.name)
        except KeyError:
            return {"ok": False, "error": f"unknown tool: {tc.name}"}
        try:
            return tool.handler(**tc.arguments)
        except Exception as e:  # noqa: BLE001 — 工具可能抛任意异常，统一转成结构化错误
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}
