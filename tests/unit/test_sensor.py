"""Tests for MeasureIt sensor class."""

from datetime import datetime, timedelta
from unittest import mock
from unittest.mock import AsyncMock, MagicMock
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

from custom_components.measureit.const import PREDEFINED_PERIODS, SensorState
from custom_components.measureit.meter import CounterMeter, SourceMeter, TimeMeter
from custom_components.measureit.sensor import (
    MeasureItSensor,
    MeasureItSensorStoredData,
)


@pytest.fixture(name="test_now")
def fixture_datetime_now():
    """Fixture for datetime.now."""
    return datetime(2025, 1, 1, 10, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)


@pytest.fixture(name="day_sensor")
def fixture_day_sensor(hass: HomeAssistant, test_now: datetime):
    """Fixture for creating a MeasureIt sensor."""
    mockMeter = MagicMock()
    mockMeter.measured_value = 0
    with mock.patch(
        "homeassistant.helpers.condition.dt_util.now",
        return_value=test_now,
    ):
        sensor = MeasureItSensor(
            hass,
            MagicMock(),
            mockMeter,
            "test_sensor_day",
            "test_sensor_day",
            PREDEFINED_PERIODS["day"],
            lambda x: x,
            SensorStateClass.TOTAL,
            SensorDeviceClass.DURATION,
            "hours",
        )
        sensor.entity_id = "sensor.test_sensor_day"
        yield sensor
        sensor.unsub_reset_listener()


@pytest.fixture(name="real_meter_sensor")
def fixture_real_meter_sensor(hass: HomeAssistant, test_now: datetime):
    """Fixture for creating a MeasureIt sensor."""
    with mock.patch(
        "homeassistant.helpers.condition.dt_util.now",
        return_value=test_now,
    ):
        sensor = MeasureItSensor(
            hass,
            MagicMock(),
            CounterMeter(),
            "test_sensor_day",
            "test_sensor_day",
            PREDEFINED_PERIODS["day"],
            lambda x: x,
            SensorStateClass.TOTAL,
        )
        sensor.entity_id = "sensor.test_sensor_day"
        yield sensor
        sensor.unsub_reset_listener()


@pytest.fixture(name="restore_sensor")
def fixture_restore_sensor(hass: HomeAssistant, test_now: datetime):
    """Fixture for creating a MeasureIt sensor."""
    with mock.patch(
        "homeassistant.helpers.condition.dt_util.now",
        return_value=test_now,
    ):
        sensor = MeasureItSensor(
            hass,
            MagicMock(),
            CounterMeter(),
            "test_sensor_day",
            "test_sensor_day",
            PREDEFINED_PERIODS["day"],
            lambda x: x,
            SensorStateClass.TOTAL_INCREASING,
        )
        sensor.entity_id = "sensor.test_sensor_day"
        data = {
            "meter_data": {
                "measured_value": 123,
                "prev_measured_value": 256,
                "measuring": False,
            },
            "last_reset": "2025-01-01T00:00:00-08:00",
            "next_reset": "2025-01-02T00:00:00-08:00",
            "time_window_active": True,
            "condition_active": False,
        }
        stored_data = MeasureItSensorStoredData.from_dict(data)
        stored_data_mock = AsyncMock()
        stored_data_mock.return_value = stored_data
        sensor.async_get_last_sensor_data = stored_data_mock
        yield sensor
        sensor.unsub_reset_listener()


@pytest.fixture(name="none_sensor")
def fixture_none_sensor(hass: HomeAssistant, test_now: datetime):
    """Fixture for creating a MeasureIt sensor."""
    mockMeter = MagicMock()
    mockMeter.measured_value = 0
    with mock.patch(
        "homeassistant.helpers.condition.dt_util.now",
        return_value=test_now,
    ):
        sensor = MeasureItSensor(
            hass,
            MagicMock(),
            mockMeter,
            "test_sensor_day",
            "test_sensor_day",
            None,
            lambda x: x,
            SensorStateClass.TOTAL,
        )
        sensor.entity_id = "sensor.test_sensor_none"
        yield sensor
        sensor.unsub_reset_listener()


def test_day_sensor_init(day_sensor: MeasureItSensor, test_now: datetime):
    """Test sensor initialization."""
    assert day_sensor.native_value == 0
    assert day_sensor.unit_of_measurement == "hours"
    assert day_sensor.state_class == SensorStateClass.TOTAL
    assert day_sensor.device_class == SensorDeviceClass.DURATION


def test_none_sensor_init(none_sensor: MeasureItSensor, test_now: datetime):
    """Test sensor initialization."""
    assert none_sensor.native_value == 0
    assert none_sensor.next_reset is None
    assert none_sensor.unit_of_measurement is None
    assert none_sensor.state_class is SensorStateClass.TOTAL
    assert none_sensor.device_class is None


def test_sensor_state_on_condition_timewindow_change(
    real_meter_sensor: MeasureItSensor,
):
    """Test sensor state update on condition template change."""
    sensor = real_meter_sensor
    assert sensor.sensor_state == SensorState.WAITING_FOR_TIME_WINDOW
    assert sensor.meter.measuring is False
    sensor.on_time_window_change(True)
    assert sensor.sensor_state == SensorState.WAITING_FOR_CONDITION
    sensor.on_condition_template_change(True)
    assert sensor.sensor_state == SensorState.MEASURING
    assert sensor.meter.measuring is True
    sensor.on_condition_template_change(False)
    assert sensor.sensor_state == SensorState.WAITING_FOR_CONDITION
    sensor.on_time_window_change(False)
    assert sensor.sensor_state == SensorState.WAITING_FOR_TIME_WINDOW
    sensor.on_condition_template_change(True)
    assert sensor.sensor_state == SensorState.WAITING_FOR_TIME_WINDOW
    assert sensor.meter.measuring is False


def test_scheduled_reset_in_past(day_sensor: MeasureItSensor, test_now: datetime):
    """Test sensor reset when scheduled in past."""
    with mock.patch(
        "homeassistant.helpers.condition.dt_util.now",
        return_value=datetime(2025, 1, 1, 12, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE),
    ):
        day_sensor.reset = mock.MagicMock()
        day_sensor.schedule_next_reset(test_now + timedelta(hours=1))
    assert day_sensor.reset.call_count == 1


def test_scheduled_reset_in_future(day_sensor: MeasureItSensor, test_now: datetime):
    """Test sensor reset when scheduled in past."""
    with mock.patch(
        "homeassistant.helpers.condition.dt_util.now",
        return_value=datetime(2025, 1, 1, 10, 30, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE),
    ):
        day_sensor.reset = mock.MagicMock()
        day_sensor.schedule_next_reset(test_now + timedelta(hours=1))

    assert day_sensor.reset.call_count == 0
    assert day_sensor.next_reset == test_now + timedelta(hours=1)

    with mock.patch(
        "homeassistant.helpers.condition.dt_util.now",
        return_value=datetime(2025, 1, 3, 12, 30, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE),
    ):
        day_sensor.schedule_next_reset()
    assert day_sensor.next_reset == datetime(
        2025, 1, 4, 0, 00, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )


def test_scheduled_reset_none_sensor(none_sensor: MeasureItSensor):
    """Test sensor reset when scheduled in past."""
    with mock.patch(
        "homeassistant.helpers.condition.dt_util.now",
        return_value=datetime(2025, 1, 1, 12, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE),
    ):
        none_sensor.reset = mock.MagicMock()
        none_sensor.schedule_next_reset(
            datetime(2025, 1, 1, 13, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
        )
    assert none_sensor.reset.call_count == 0
    assert none_sensor.next_reset == datetime(
        2025, 1, 1, 13, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )
    none_sensor.schedule_next_reset()
    assert none_sensor.next_reset is None


async def test_reset_sensor(none_sensor: MeasureItSensor, test_now: datetime):
    """Test sensor reset."""
    assert none_sensor.next_reset is None
    none_sensor.reset()
    assert none_sensor.meter.reset.called_once
    assert none_sensor.next_reset is None
    assert none_sensor._attr_last_reset == test_now


def test_on_value_change(day_sensor: MeasureItSensor):
    """Test sensor value change."""
    day_sensor.meter = CounterMeter()
    day_sensor.on_condition_template_change(True)
    day_sensor.on_time_window_change(True)
    day_sensor.on_value_change(1)
    assert day_sensor.native_value == 1
    day_sensor.on_value_change(1)
    assert day_sensor.native_value == 2


def test_on_value_change_for_time(day_sensor: MeasureItSensor):
    """Test sensor value change for time."""
    day_sensor.meter = TimeMeter()
    day_sensor.on_condition_template_change(True)
    day_sensor.on_time_window_change(True)
    day_sensor.on_value_change()
    assert day_sensor.native_value > 0


def test_none_sensor_stored_data(none_sensor: MeasureItSensor):
    """Test sensor restore."""
    data = MeasureItSensorStoredData(
        meter_data=none_sensor.meter.to_dict(),
        last_reset=none_sensor.last_reset,
        next_reset=none_sensor.next_reset,
        time_window_active=none_sensor._time_window_active,
        condition_active=none_sensor._condition_active,
    )

    stored = data.as_dict()
    restored = MeasureItSensorStoredData.from_dict(stored)
    assert data == restored
    assert restored.time_window_active is False
    assert restored.condition_active is False
    assert restored.next_reset is None


def test_day_sensor_stored_data(day_sensor: MeasureItSensor):
    """Test sensor restore."""
    data = MeasureItSensorStoredData(
        meter_data=day_sensor.meter.to_dict(),
        last_reset=day_sensor.last_reset,
        next_reset=day_sensor.next_reset,
        time_window_active=day_sensor._time_window_active,
        condition_active=day_sensor._condition_active,
    )

    stored = data.as_dict()
    restored = MeasureItSensorStoredData.from_dict(stored)
    assert data == restored
    assert restored.time_window_active is False
    assert restored.condition_active is False
    assert restored.next_reset == day_sensor.next_reset
    assert restored.last_reset == day_sensor.last_reset


def test_restore_from_data():
    """Test sensor restore from json."""
    data = {
        "meter_data": {
            "measured_value": 0,
            "measuring": False,
        },
        "last_reset": "2025-01-01T00:00:00-08:00",
        "next_reset": "2025-01-02T00:00:00+00:00",
        "time_window_active": True,
        "condition_active": False,
    }
    restored = MeasureItSensorStoredData.from_dict(data)
    assert restored.time_window_active is True
    assert restored.condition_active is False
    assert restored.last_reset == datetime(
        2025, 1, 1, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )
    assert restored.next_reset == datetime(2025, 1, 2, 0, 0, 0, tzinfo=dt_util.UTC)
    assert restored.meter_data["measured_value"] == 0
    assert restored.meter_data["measuring"] is False


def test_restore_old_format_state_measuring():
    """Test sensor restore with old format."""
    data = {
        "measured_value": 2880.001408100128,
        "start_measured_value": 2700,
        "prev_measured_value": 180.00166988372803,
        "session_start_reading": 1705914000.004058,
        "period_last_reset": 1705914000.004091,
        "period_end": 1706119200.0,
        "state": "measuring",
    }
    restored = MeasureItSensorStoredData.from_dict(data)
    assert restored.time_window_active is True
    assert restored.condition_active is True
    assert restored.next_reset == datetime(
        2024, 1, 24, 10, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )
    assert restored.last_reset is not None
    assert restored.meter_data["measured_value"] == 2880.001408100128
    assert restored.meter_data["measuring"] is True
    assert restored.meter_data["session_start_measured_value"] == 2700
    assert restored.meter_data["prev_measured_value"] == 180.00166988372803
    assert restored.meter_data["session_start_value"] == 1705914000.004058


def test_restore_old_format_state_not_measuring():
    """Test sensor restore with old format."""
    data = {
        "measured_value": 2880.001408100128,
        "start_measured_value": 0,
        "prev_measured_value": 180.00166988372803,
        "session_start_reading": 1705914000.004058,
        "period_last_reset": 1705914000.004091,
        "period_end": 1706119200.0,
        "state": "waiting for condition",
    }
    restored = MeasureItSensorStoredData.from_dict(data)
    assert restored.time_window_active is True
    assert restored.condition_active is False
    assert restored.next_reset is not None
    assert restored.last_reset is not None
    assert restored.meter_data["measured_value"] == 2880.001408100128
    assert restored.meter_data["measuring"] is False
    assert restored.meter_data["session_start_measured_value"] == 0
    assert restored.meter_data["prev_measured_value"] == 180.00166988372803
    assert restored.meter_data["session_start_value"] == 1705914000.004058


async def test_added_to_hass(day_sensor: MeasureItSensor, test_now: datetime):
    """Test sensor added to hass."""
    await day_sensor.async_added_to_hass()
    assert day_sensor._coordinator.register.call_count == 1
    assert day_sensor.next_reset == (test_now + timedelta(days=1)).replace(
        hour=0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )


async def test_added_to_hass_with_restore(restore_sensor: MeasureItSensor):
    """Test sensor added to hass."""
    await restore_sensor.async_added_to_hass()
    assert restore_sensor.last_reset == datetime(
        2025, 1, 1, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )
    assert restore_sensor.next_reset == datetime(
        2025, 1, 2, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )
    assert restore_sensor.native_value == 123
    assert restore_sensor.meter.prev_measured_value == 256
    assert restore_sensor._time_window_active is True
    assert restore_sensor._condition_active is False
    assert restore_sensor.sensor_state == SensorState.WAITING_FOR_CONDITION


def test_extra_restore_state_data_property(day_sensor: MeasureItSensor):
    """Test getting extra restore state data."""
    day_sensor.meter = SourceMeter()
    day_sensor.meter.update(100)
    day_sensor.on_condition_template_change(True)
    day_sensor.on_time_window_change(True)
    day_sensor.on_value_change(200)
    stored_data = day_sensor.extra_restore_state_data
    assert stored_data.meter_data["measured_value"] == 100
    assert stored_data.condition_active is True
    assert stored_data.time_window_active is True
    day_sensor.on_condition_template_change(False)
    stored_data = day_sensor.extra_restore_state_data
    assert stored_data.condition_active is False
