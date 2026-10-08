from enum import Enum

from pydantic import BaseModel


class DeviceType(str, Enum):
    LIGHT = "light"
    AC = "ac"


class DeviceState(BaseModel):
    on: bool = False
    temperature: int | None = None


class Device(BaseModel):
    id: str
    name: str
    type: DeviceType
    room: str
    state: DeviceState
