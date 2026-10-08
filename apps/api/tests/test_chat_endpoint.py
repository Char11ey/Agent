import pytest
from fastapi.testclient import TestClient

from app.agent.loop import AgentLoop
from app.agent.tools import ToolRegistry, make_iot_tools
from app.iot.service import MockIoTService
from app.llm.base import LLMResponse, ToolCall
from app.llm.fake import FakeProvider
from app.main import app
from app.state import set_agent


@pytest.fixture
def client():
    return TestClient(app)


def _install_fake_agent(scripted: list[LLMResponse]) -> MockIoTService:
    iot = MockIoTService.with_seed_data()
    reg = ToolRegistry()
    for t in make_iot_tools(iot):
        reg.register(t)
    set_agent(AgentLoop(llm=FakeProvider(responses=scripted), registry=reg), iot)
    return iot


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_devices_endpoint(client):
    _install_fake_agent([])
    r = client.get("/api/devices")
    assert r.status_code == 200
    devices = r.json()
    assert len(devices) >= 4
    assert any(d["id"] == "light-living-1" for d in devices)


def test_chat_sse_emits_events(client):
    scripted = [
        LLMResponse(
            text=None,
            tool_calls=[ToolCall(id="c1", name="turn_on_light", arguments={"room": "客厅", "on": True})],
            usage={},
        ),
        LLMResponse(text="已开灯", tool_calls=[], usage={"total_tokens": 12}),
    ]
    _install_fake_agent(scripted)

    with client.stream(
        "POST",
        "/api/chat",
        json={"message": "把客厅灯打开", "session_id": "s1"},
    ) as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]
        body = "".join(r.iter_text())

    assert "event: tool_call" in body
    assert "event: tool_result" in body
    assert "event: text_delta" in body
    assert "event: done" in body


def test_chat_requires_message(client):
    r = client.post("/api/chat", json={"session_id": "s1"})
    assert r.status_code == 422


def test_chat_without_agent_returns_503(client):
    """未注入 agent 时返回 503 而不是 crash。"""
    from app.state import state

    state.agent = None
    r = client.post("/api/chat", json={"message": "hi", "session_id": "s1"})
    assert r.status_code == 503
