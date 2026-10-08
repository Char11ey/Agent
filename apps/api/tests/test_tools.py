import pytest

from app.agent.tools import Tool, ToolRegistry, make_iot_tools
from app.iot.models import DeviceType
from app.iot.service import MockIoTService


def test_make_iot_tools_returns_two():
    tools = make_iot_tools(MockIoTService.with_seed_data())
    names = [t.name for t in tools]
    assert names == ["turn_on_light", "set_temperature"]


def test_turn_on_light_handler(iot: MockIoTService):
    tools = {t.name: t for t in make_iot_tools(iot)}
    result = tools["turn_on_light"].handler(room="客厅", on=True)
    assert result["ok"] is True
    assert result["devices"][0]["state"]["on"] is True


def test_turn_on_light_room_without_light(iot: MockIoTService):
    tools = {t.name: t for t in make_iot_tools(iot)}
    result = tools["turn_on_light"].handler(room="厨房", on=True)
    assert result["ok"] is False
    assert "no light" in result["error"].lower()


def test_set_temperature_handler(iot: MockIoTService):
    tools = {t.name: t for t in make_iot_tools(iot)}
    result = tools["set_temperature"].handler(room="卧室", temperature=22)
    assert result["ok"] is True
    assert result["devices"][0]["state"]["temperature"] == 22


def test_set_temperature_out_of_range(iot: MockIoTService):
    tools = {t.name: t for t in make_iot_tools(iot)}
    with pytest.raises(ValueError, match="temperature"):
        tools["set_temperature"].handler(room="卧室", temperature=99)


def test_registry_openai_schemas():
    reg = ToolRegistry()
    reg.register(Tool(
        name="demo",
        description="demo tool",
        parameters={"type": "object", "properties": {"x": {"type": "integer"}}},
        handler=lambda x: {"ok": True},
    ))
    schemas = reg.openai_schemas()
    assert schemas[0]["type"] == "function"
    assert schemas[0]["function"]["name"] == "demo"
    assert "properties" in schemas[0]["function"]["parameters"]


def test_registry_get_missing_raises():
    reg = ToolRegistry()
    with pytest.raises(KeyError):
        reg.get("nope")
