import pytest

from app.iot.service import MockIoTService


@pytest.fixture
def iot() -> MockIoTService:
    return MockIoTService.with_seed_data()
