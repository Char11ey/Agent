from collections import deque

from app.llm.base import LLMResponse


class FakeProvider:
    """测试专用：从预设队列中按顺序返回响应。队列空了抛 RuntimeError。"""

    def __init__(self, responses: list[LLMResponse]):
        self._queue: deque[LLMResponse] = deque(responses)
        self.calls: list[tuple[list[dict], list[dict]]] = []

    async def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        self.calls.append((messages, tools))
        if not self._queue:
            raise RuntimeError("FakeProvider: scripted responses exhausted")
        return self._queue.popleft()
