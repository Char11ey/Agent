import pytest

from app.iot.models import DeviceType
from app.iot.service import MockIoTService


def test_seed_data_has_devices(iot: MockIoTService):
    devices = iot.list_devices()
    assert len(devices) >= 4  # 至少有 2 灯 + 2 空调


def test_get_device_returns_seeded(iot: MockIoTService):
    d = iot.get_device("light-living-1")
    assert d.type == DeviceType.LIGHT
    assert d.room == "客厅"


def test_get_device_missing_raises(iot: MockIoTService):
    with pytest.raises(KeyError):
        iot.get_device("nonexistent")


def test_find_devices_by_room_and_type(iot: MockIoTService):
    lights = iot.find_devices(room="客厅", type=DeviceType.LIGHT)
    assert len(lights) >= 1
    assert all(d.room == "客厅" and d.type == DeviceType.LIGHT for d in lights)


def test_set_state_on_off(iot: MockIoTService):
    d = iot.set_state("light-living-1", on=True)
    assert d.state.on is True
    d = iot.set_state("light-living-1", on=False)
    assert d.state.on is False


def test_set_state_temperature(iot: MockIoTService):
    d = iot.set_state("ac-living-1", temperature=26)
    assert d.state.temperature == 26


def test_set_state_invalid_temp_raises(iot: MockIoTService):
    with pytest.raises(ValueError):
        iot.set_state("ac-living-1", temperature=99)
