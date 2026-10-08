from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.iot.models import DeviceType
from app.iot.service import MockIoTService


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    handler: Callable[..., dict]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        return self._tools[name]

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def openai_schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]


def make_iot_tools(iot: MockIoTService) -> list[Tool]:
    def turn_on_light(room: str, on: bool = True) -> dict:
        lights = iot.find_devices(room=room, type=DeviceType.LIGHT)
        if not lights:
            return {"ok": False, "error": f"no light found in room: {room}"}
        updated = [iot.set_state(d.id, on=on) for d in lights]
        return {"ok": True, "devices": [d.model_dump() for d in updated]}

    def set_temperature(room: str, temperature: int) -> dict:
        acs = iot.find_devices(room=room, type=DeviceType.AC)
        if not acs:
            return {"ok": False, "error": f"no AC found in room: {room}"}
        updated = [iot.set_state(d.id, temperature=temperature) for d in acs]
        return {"ok": True, "devices": [d.model_dump() for d in updated]}

    return [
        Tool(
            name="turn_on_light",
            description="Turn on or off all lights in a given room. Use this when the user asks to control lights.",
            parameters={
                "type": "object",
                "properties": {
                    "room": {
                        "type": "string",
                        "description": "The room name, e.g. '客厅' or '卧室'.",
                    },
                    "on": {
                        "type": "boolean",
                        "description": "true to turn on, false to turn off. Default true.",
                    },
                },
                "required": ["room"],
            },
            handler=turn_on_light,
        ),
        Tool(
            name="set_temperature",
            description="Set the AC temperature in a given room. Temperature range is 16-30 Celsius.",
            parameters={
                "type": "object",
                "properties": {
                    "room": {
                        "type": "string",
                        "description": "The room name, e.g. '客厅' or '卧室'.",
                    },
                    "temperature": {
                        "type": "integer",
                        "description": "Target temperature in Celsius, between 16 and 30.",
                    },
                },
                "required": ["room", "temperature"],
            },
            handler=set_temperature,
        ),
    ]
