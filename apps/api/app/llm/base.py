from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)


class LLMProvider(Protocol):
    async def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        """调用 LLM。messages 用 OpenAI 格式；tools 是 OpenAI function-calling schema 列表。"""
        ...
