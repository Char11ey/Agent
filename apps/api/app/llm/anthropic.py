import json
from typing import Any

from anthropic import AsyncAnthropic

from app.config import Settings
from app.llm.base import LLMResponse, ToolCall


class AnthropicProvider:
    """Anthropic Messages API 接入。

    Messages API 用 tool_use content block，与 OpenAI 的 tool_calls 结构不同；
    这里在边界做适配，让上层 AgentLoop 只见 OpenAI 风格。
    """

    def __init__(self, settings: Settings):
        if not settings.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. Export it or put it in .env."
            )
        self.model = settings.anthropic_model
        client_kwargs: dict[str, Any] = {"api_key": settings.anthropic_api_key}
        if settings.anthropic_base_url:
            client_kwargs["base_url"] = settings.anthropic_base_url
        self._client = AsyncAnthropic(**client_kwargs)

    async def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        # Anthropic 用 system 单独字段而不是 system message
        system = None
        anthropic_messages = []
        for m in messages:
            role = m.get("role")
            if role == "system":
                system = m.get("content", "")
                continue
            anthropic_messages.append(self._to_anthropic_message(m))

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": anthropic_messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._to_anthropic_tools(tools)

        resp = await self._client.messages.create(**kwargs)
        return self._to_llm_response(resp)

    def _to_anthropic_message(self, m: dict) -> dict:
        """把 OpenAI 格式的单条消息转 Anthropic 格式。"""
        role = m.get("role")
        content = m.get("content")
        tool_calls = m.get("tool_calls")

        if role == "assistant":
            blocks: list[dict] = []
            if content:
                blocks.append({"type": "text", "text": content})
            for tc in tool_calls or []:
                args = tc["function"]["arguments"]
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"__invalid_json__": args}
                blocks.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "input": args,
                })
            return {"role": "assistant", "content": blocks or [{"type": "text", "text": ""}]}

        if role == "tool":
            # OpenAI: {"role":"tool", "tool_call_id": ..., "content": ...}
            # Anthropic: user message with tool_result block
            return {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": m["tool_call_id"],
                        "content": m.get("content", ""),
                    }
                ],
            }

        # user / 其他
        return {"role": "user", "content": content if isinstance(content, str) else str(content)}

    def _to_anthropic_tools(self, openai_tools: list[dict]) -> list[dict]:
        out = []
        for t in openai_tools:
            fn = t.get("function", t)
            out.append({
                "name": fn["name"],
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
            })
        return out

    def _to_llm_response(self, resp: Any) -> LLMResponse:
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
            elif getattr(block, "type", None) == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=dict(block.input))
                )

        usage = {}
        if getattr(resp, "usage", None) is not None:
            usage = {
                "prompt_tokens": resp.usage.input_tokens,
                "completion_tokens": resp.usage.output_tokens,
                "total_tokens": resp.usage.input_tokens + resp.usage.output_tokens,
            }

        text = "\n".join(text_parts) if text_parts else None
        return LLMResponse(text=text, tool_calls=tool_calls, usage=usage)
