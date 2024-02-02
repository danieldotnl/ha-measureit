"""Tests for MeasureIt sensor class."""
from datetime import datetime, timedelta
from unittest import mock
from unittest.mock import MagicMock
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

from custom_components.measureit.const import PREDEFINED_PERIODS, SensorState
from custom_components.measureit.meter import CounterMeter
from custom_components.measureit.sensor import MeasureItSensor


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
            "hours",
            SensorStateClass.TOTAL,
            SensorDeviceClass.DURATION,
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
        )
        sensor.entity_id = "sensor.test_sensor_day"
        sensor.async_get_last_sensor_data = MagicMock()
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
        )
        sensor.entity_id = "sensor.test_sensor_none"
        yield sensor
        sensor.unsub_reset_listener()


# def test_meter_after_sensor_restore():
#     """Test meter after sensor restore."""
#     assert True


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
    assert none_sensor.state_class is None
    assert none_sensor.device_class is None


async def test_added_to_hass(
    day_sensor: MeasureItSensor, hass: HomeAssistant, test_now: datetime
):
    """Test sensor added to hass."""
    await day_sensor.async_added_to_hass()
    assert day_sensor._coordinator.register.call_count == 1
    assert day_sensor.next_reset == (test_now + timedelta(days=1)).replace(
        hour=0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )


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
