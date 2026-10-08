from app.iot.models import Device, DeviceState, DeviceType


class MockIoTService:
    """内存 Mock IoT 服务。真实项目里这里换成米家/MQTT 客户端；接口保持不变。"""

    def __init__(self, devices: list[Device] | None = None):
        self._devices: dict[str, Device] = {d.id: d for d in (devices or [])}

    @classmethod
    def with_seed_data(cls) -> "MockIoTService":
        return cls(
            devices=[
                Device(
                    id="light-living-1", name="客厅主灯", type=DeviceType.LIGHT, room="客厅",
                    state=DeviceState(on=False),
                ),
                Device(
                    id="light-bedroom-1", name="卧室吸顶灯", type=DeviceType.LIGHT, room="卧室",
                    state=DeviceState(on=False),
                ),
                Device(
                    id="ac-living-1", name="客厅空调", type=DeviceType.AC, room="客厅",
                    state=DeviceState(on=False, temperature=26),
                ),
                Device(
                    id="ac-bedroom-1", name="卧室空调", type=DeviceType.AC, room="卧室",
                    state=DeviceState(on=False, temperature=26),
                ),
            ]
        )

    def list_devices(self) -> list[Device]:
        return list(self._devices.values())

    def get_device(self, device_id: str) -> Device:
        if device_id not in self._devices:
            raise KeyError(f"device not found: {device_id}")
        return self._devices[device_id]

    def find_devices(self, room: str, type: DeviceType) -> list[Device]:
        return [d for d in self._devices.values() if d.room == room and d.type == type]

    def set_state(
        self,
        device_id: str,
        *,
        on: bool | None = None,
        temperature: int | None = None,
    ) -> Device:
        if device_id not in self._devices:
            raise KeyError(f"device not found: {device_id}")
        if temperature is not None and not (16 <= temperature <= 30):
            raise ValueError(f"temperature out of range [16, 30]: {temperature}")
        current = self._devices[device_id]
        new_state = current.state.model_copy()
        if on is not None:
            new_state.on = on
        if temperature is not None:
            new_state.temperature = temperature
        updated = current.model_copy(update={"state": new_state})
        self._devices[device_id] = updated
        return updated
