"""Tests for MeasureIt sensor class."""

import logging
from datetime import datetime, timedelta
from unittest import mock
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

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
    mock_meter = MagicMock()
    mock_meter.measured_value = 0
    with mock.patch(
        "homeassistant.helpers.condition.dt_util.now",
        return_value=test_now,
    ):
        sensor = MeasureItSensor(
            hass,
            MagicMock(),
            mock_meter,
            "test_sensor_day",
            "test_sensor_day",
            PREDEFINED_PERIODS["day"],
            lambda x: x,
            SensorStateClass.TOTAL,
            SensorDeviceClass.DURATION,
            "h",
        )
        sensor.entity_id = "sensor.test_sensor_day"
        yield sensor
        sensor.unsub_reset_listener()


@pytest.fixture(name="month_sensor")
def fixture_month_sensor(hass: HomeAssistant, test_now: datetime):
    """Fixture for creating a MeasureIt sensor which resets monthly."""
    mock_meter = MagicMock()
    mock_meter.measured_value = 0
    with mock.patch(
        "homeassistant.helpers.condition.dt_util.now",
        return_value=test_now,
    ):
        sensor = MeasureItSensor(
            hass,
            MagicMock(),
            mock_meter,
            "test_sensor_month",
            "test_sensor_month",
            PREDEFINED_PERIODS["month"],
            lambda x: x,
            SensorStateClass.TOTAL,
            SensorDeviceClass.DURATION,
            "h",
        )
        sensor.entity_id = "sensor.test_sensor_month"
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
            SensorStateClass.TOTAL,
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
            "active": False,
        }
        stored_data = MeasureItSensorStoredData.from_dict(data)
        stored_data_mock = AsyncMock()
        stored_data_mock.return_value = stored_data
        sensor.async_get_last_sensor_data = stored_data_mock
        yield sensor
        sensor.unsub_reset_listener()


@pytest.fixture(name="restore_sensor_old_format")
def fixture_restore_sensor_old_format(hass: HomeAssistant, test_now: datetime):
    """
    Fixture for creating a MeasureIt sensor with old 'condition_active' field.

    This simulates a sensor that was saved with v0.8.2 or earlier and is being
    restored after upgrading to v0.8.3/v0.5.1+.
    """
    with mock.patch(
        "homeassistant.helpers.condition.dt_util.now",
        return_value=test_now,
    ):
        sensor = MeasureItSensor(
            hass,
            MagicMock(),
            CounterMeter(),
            "test_sensor_year",
            "test_sensor_year",
            PREDEFINED_PERIODS["day"],  # Use day instead of year to avoid reset
            lambda x: x,
            SensorStateClass.TOTAL,
        )
        sensor.entity_id = "sensor.test_sensor_year"
        # Data with old field name 'condition_active' from v0.8.2
        data = {
            "meter_data": {
                "measured_value": 8760,  # A full year of hours
                "prev_measured_value": 8500,
                "measuring": True,
            },
            "last_reset": "2024-12-31T00:00:00-08:00",
            "next_reset": "2025-01-02T00:00:00-08:00",  # Future relative to test_now
            "time_window_active": True,
            "condition_active": True,  # Old field name - CRITICAL to test!
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
    mock_meter = MagicMock()
    mock_meter.measured_value = 0
    mock_meter.prev_measured_value = 0
    with mock.patch(
        "homeassistant.helpers.condition.dt_util.now",
        return_value=test_now,
    ):
        sensor = MeasureItSensor(
            hass,
            MagicMock(),
            mock_meter,
            "test_sensor_day",
            "test_sensor_day",
            None,
            lambda x: x,
            SensorStateClass.TOTAL,
        )
        sensor.entity_id = "sensor.test_sensor_none"
        yield sensor
        sensor.unsub_reset_listener()


def test_day_sensor_init(day_sensor: MeasureItSensor, test_now: datetime) -> None:
    """Test sensor initialization."""
    assert day_sensor.native_value == 0
    assert day_sensor.unit_of_measurement == "h"
    assert day_sensor.state_class == SensorStateClass.TOTAL
    assert day_sensor.device_class == SensorDeviceClass.DURATION


def test_none_sensor_init(none_sensor: MeasureItSensor, test_now: datetime) -> None:
    """Test sensor initialization."""
    assert none_sensor.native_value == 0
    assert none_sensor._next_reset is None
    assert none_sensor.unit_of_measurement is None
    assert none_sensor.state_class is SensorStateClass.TOTAL
    assert none_sensor.device_class is None


def test_sensor_state_on_condition_timewindow_change(
    real_meter_sensor: MeasureItSensor,
) -> None:
    """Test sensor state update on condition template change."""
    sensor = real_meter_sensor
    assert sensor.sensor_state == SensorState.WAITING_FOR_TIME_WINDOW
    assert sensor.meter.measuring is False
    sensor.on_time_window_change(active=True)
    assert sensor.sensor_state == SensorState.WAITING_FOR_CONDITION
    sensor.on_condition_template_change(active=True)
    assert sensor.sensor_state == SensorState.MEASURING
    assert sensor.meter.measuring is True
    sensor.on_condition_template_change(active=False)
    assert sensor.sensor_state == SensorState.WAITING_FOR_CONDITION
    sensor.on_time_window_change(active=False)
    assert sensor.sensor_state == SensorState.WAITING_FOR_TIME_WINDOW
    sensor.on_condition_template_change(active=True)
    assert sensor.sensor_state == SensorState.WAITING_FOR_TIME_WINDOW
    assert sensor.meter.measuring is False


def test_scheduled_reset_in_past(
    day_sensor: MeasureItSensor, test_now: datetime
) -> None:
    """Test sensor reset when scheduled in past."""
    with mock.patch(
        "homeassistant.helpers.condition.dt_util.now",
        return_value=datetime(2025, 1, 1, 12, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE),
    ):
        day_sensor.reset = mock.MagicMock()
        day_sensor.schedule_next_reset(test_now + timedelta(hours=1))
    assert day_sensor.reset.call_count == 1


def test_scheduled_reset_in_future(
    day_sensor: MeasureItSensor, test_now: datetime
) -> None:
    """Test sensor reset when scheduled in past."""
    with mock.patch(
        "homeassistant.helpers.condition.dt_util.now",
        return_value=datetime(2025, 1, 1, 10, 30, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE),
    ):
        day_sensor.reset = mock.MagicMock()
        day_sensor.schedule_next_reset(test_now + timedelta(hours=1))

    assert day_sensor.reset.call_count == 0
    assert day_sensor._next_reset == test_now + timedelta(hours=1)

    with mock.patch(
        "homeassistant.helpers.condition.dt_util.now",
        return_value=datetime(2025, 1, 3, 12, 30, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE),
    ):
        day_sensor.schedule_next_reset()
    assert day_sensor._next_reset == datetime(
        2025, 1, 4, 0, 00, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )


def test_scheduled_reset_none_sensor(none_sensor: MeasureItSensor) -> None:
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
    assert none_sensor._next_reset == datetime(
        2025, 1, 1, 13, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )
    none_sensor.schedule_next_reset()
    assert none_sensor._next_reset is None


async def test_reset_sensor(none_sensor: MeasureItSensor, test_now: datetime) -> None:
    """Test sensor reset."""
    assert none_sensor._next_reset is None
    none_sensor.reset()
    none_sensor.meter.reset.assert_called_once()
    assert none_sensor._next_reset is None
    assert none_sensor._last_reset == test_now


def test_on_value_change(day_sensor: MeasureItSensor) -> None:
    """Test sensor value change."""
    day_sensor.meter = CounterMeter()
    day_sensor.on_condition_template_change(active=True)
    day_sensor.on_time_window_change(active=True)
    day_sensor.on_value_change(1)
    assert day_sensor.native_value == 1
    day_sensor.on_value_change(1)
    assert day_sensor.native_value == 2


def test_on_value_change_for_time(day_sensor: MeasureItSensor) -> None:
    """Test sensor value change for time."""
    day_sensor.meter = TimeMeter()
    day_sensor.on_condition_template_change(active=True)
    day_sensor.on_time_window_change(active=True)
    day_sensor.on_value_change()
    assert day_sensor.meter.measured_value > 0


def test_none_sensor_stored_data(none_sensor: MeasureItSensor) -> None:
    """Test sensor restore."""
    data = MeasureItSensorStoredData(
        meter_data=none_sensor.meter.to_dict(),
        last_reset=none_sensor._last_reset,
        next_reset=none_sensor._next_reset,
        time_window_active=none_sensor._time_window_active,
        active=none_sensor._active,
    )

    stored = data.as_dict()
    restored = MeasureItSensorStoredData.from_dict(stored)
    assert data == restored
    assert restored.time_window_active is False
    assert restored.active is False
    assert restored.next_reset is None


def test_day_sensor_stored_data(day_sensor: MeasureItSensor) -> None:
    """Test sensor restore."""
    data = MeasureItSensorStoredData(
        meter_data=day_sensor.meter.to_dict(),
        last_reset=day_sensor._last_reset,
        next_reset=day_sensor._next_reset,
        time_window_active=day_sensor._time_window_active,
        active=day_sensor._active,
    )

    stored = data.as_dict()
    restored = MeasureItSensorStoredData.from_dict(stored)
    assert data == restored
    assert restored.time_window_active is False
    assert restored.active is False
    assert restored.next_reset == day_sensor._next_reset
    assert restored.last_reset == day_sensor._last_reset


def test_restore_from_data() -> None:
    """Test sensor restore from json."""
    data = {
        "meter_data": {
            "measured_value": 0,
            "measuring": False,
        },
        "last_reset": "2025-01-01T00:00:00-08:00",
        "next_reset": "2025-01-02T00:00:00+00:00",
        "time_window_active": True,
        "active": False,
    }
    restored = MeasureItSensorStoredData.from_dict(data)
    assert restored.time_window_active is True
    assert restored.active is False
    assert restored.last_reset == datetime(
        2025, 1, 1, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )
    assert restored.next_reset == datetime(2025, 1, 2, 0, 0, 0, tzinfo=dt_util.UTC)
    assert restored.meter_data["measured_value"] == 0
    assert restored.meter_data["measuring"] is False


def test_restore_old_format_state_measuring() -> None:
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
    assert restored.active is True
    assert restored.next_reset == datetime(
        2024, 1, 24, 10, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )
    assert restored.last_reset is not None
    assert restored.meter_data["measured_value"] == 2880.001408100128
    assert restored.meter_data["measuring"] is True
    assert restored.meter_data["session_start_measured_value"] == 2700
    assert restored.meter_data["prev_measured_value"] == 180.00166988372803
    assert restored.meter_data["session_start_value"] == 1705914000.004058


def test_restore_old_format_state_not_measuring() -> None:
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
    assert restored.active is False
    assert restored.next_reset is not None
    assert restored.last_reset is not None
    assert restored.meter_data["measured_value"] == 2880.001408100128
    assert restored.meter_data["measuring"] is False
    assert restored.meter_data["session_start_measured_value"] == 0
    assert restored.meter_data["prev_measured_value"] == 180.00166988372803
    assert restored.meter_data["session_start_value"] == 1705914000.004058


def test_restore_old_format_state_with_null_values() -> None:
    """Test sensor restore with old format."""
    data = {
        "measured_value": 0,
        "start_measured_value": None,
        "prev_measured_value": 0,
        "session_start_reading": None,
        "period_last_reset": 1705914000.004091,
        "period_end": 1706119200.0,
        "state": "waiting_for_time_window",
    }
    restored = MeasureItSensorStoredData.from_dict(data)
    assert restored.time_window_active is False
    assert restored.active is False
    assert restored.next_reset == datetime(
        2024, 1, 24, 10, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )
    assert restored.last_reset is not None
    assert restored.meter_data["measured_value"] == 0
    assert restored.meter_data["measuring"] is False
    assert restored.meter_data["session_start_measured_value"] == 0
    assert restored.meter_data["prev_measured_value"] == 0
    assert restored.meter_data["session_start_value"] == 0


def test_restore_migration_condition_active_to_active() -> None:
    """
    Test migration from old field name 'condition_active' to 'active'.

    This test ensures backward compatibility when restoring data saved with
    the old 'condition_active' field name (pre-v0.8.3/v0.5.1).
    CRITICAL: This prevents data loss for sensors that have been measuring
    for extended periods (months or years).
    """
    # Data saved with old field name 'condition_active' (from v0.8.2 and earlier)
    data_with_old_field_active = {
        "meter_data": {
            "measured_value": 8760.5,  # A year's worth of hours
            "prev_measured_value": 8500.0,
            "measuring": True,
        },
        "last_reset": "2024-01-01T00:00:00-08:00",
        "next_reset": "2025-01-01T00:00:00-08:00",
        "time_window_active": True,
        "condition_active": True,  # Old field name
    }
    restored = MeasureItSensorStoredData.from_dict(data_with_old_field_active)
    assert restored is not None, "CRITICAL: Restoration must not return None!"
    assert restored.time_window_active is True
    assert restored.active is True  # Should map from condition_active
    assert restored.meter_data["measured_value"] == 8760.5
    assert restored.meter_data["measuring"] is True

    # Data with old field name set to False
    data_with_old_field_inactive = {
        "meter_data": {
            "measured_value": 1234.5,
            "prev_measured_value": 1000.0,
            "measuring": False,
        },
        "last_reset": "2024-06-01T00:00:00-08:00",
        "next_reset": "2024-07-01T00:00:00-08:00",
        "time_window_active": True,
        "condition_active": False,  # Old field name
    }
    restored = MeasureItSensorStoredData.from_dict(data_with_old_field_inactive)
    assert restored is not None, "CRITICAL: Restoration must not return None!"
    assert restored.time_window_active is True
    assert restored.active is False  # Should map from condition_active
    assert restored.meter_data["measured_value"] == 1234.5


def test_restore_with_new_active_field() -> None:
    """
    Test restoration with new 'active' field name works correctly.

    Ensures that data saved with the new field name (v0.8.3/v0.5.1+)
    continues to work correctly.
    """
    data_with_new_field = {
        "meter_data": {
            "measured_value": 500.25,
            "prev_measured_value": 400.0,
            "measuring": True,
        },
        "last_reset": "2025-01-01T00:00:00-08:00",
        "next_reset": "2025-02-01T00:00:00-08:00",
        "time_window_active": True,
        "active": True,  # New field name
    }
    restored = MeasureItSensorStoredData.from_dict(data_with_new_field)
    assert restored is not None
    assert restored.time_window_active is True
    assert restored.active is True
    assert restored.meter_data["measured_value"] == 500.25


def test_restore_prefers_new_field_over_old(caplog: pytest.LogCaptureFixture) -> None:
    """
    Test that if both 'active' and 'condition_active' exist, 'active' takes precedence.

    DESIRED BEHAVIOR: This shouldn't happen in practice (indicates unusual state).
    Log a warning to alert the user, but proceed using 'active' field.
    """
    data_with_both_fields = {
        "meter_data": {
            "measured_value": 100.0,
            "prev_measured_value": 90.0,
            "measuring": True,
        },
        "last_reset": "2025-01-01T00:00:00-08:00",
        "next_reset": "2025-02-01T00:00:00-08:00",
        "time_window_active": True,
        "active": True,  # New field name (should win)
        "condition_active": False,  # Old field name (should be ignored)
    }

    with caplog.at_level(logging.WARNING):
        restored = MeasureItSensorStoredData.from_dict(data_with_both_fields)

    assert restored is not None
    assert restored.active is True  # Should use 'active', not 'condition_active'

    # Should log warning about unusual state
    assert any(
        "both 'active' and 'condition_active'" in record.message.lower()
        for record in caplog.records
    ), "Should warn when both fields are present"


def test_restore_with_missing_active_fields() -> None:
    """
    Test restoration when both 'active' and 'condition_active' are missing.

    This handles corrupted or incomplete data by defaulting to False,
    which is safer than failing completely and losing all data.
    """
    data_with_no_active_field = {
        "meter_data": {
            "measured_value": 100.0,
            "prev_measured_value": 90.0,
            "measuring": True,
        },
        "last_reset": "2025-01-01T00:00:00-08:00",
        "next_reset": "2025-02-01T00:00:00-08:00",
        "time_window_active": True,
        # Neither 'active' nor 'condition_active' present
    }
    restored = MeasureItSensorStoredData.from_dict(data_with_no_active_field)
    assert restored is not None
    assert restored.active is False  # Should default to False


async def test_added_to_hass(day_sensor: MeasureItSensor, test_now: datetime) -> None:
    """Test sensor added to hass."""
    await day_sensor.async_added_to_hass()
    assert day_sensor._coordinator.async_register_sensor.call_count == 1
    assert day_sensor._next_reset == (test_now + timedelta(days=1)).replace(
        hour=0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )


async def test_added_to_hass_with_month_period(
    month_sensor: MeasureItSensor, test_now: datetime
) -> None:
    """Test sensor added to hass."""
    await month_sensor.async_added_to_hass()
    assert month_sensor._coordinator.async_register_sensor.call_count == 1
    assert month_sensor._next_reset == datetime(
        2025, 2, 1, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )
    assert (
        month_sensor.extra_state_attributes["sensor_next_reset"]
        == "2025-02-01T00:00:00-08:00"
    )


async def test_added_to_hass_with_restore(restore_sensor: MeasureItSensor) -> None:
    """Test sensor added to hass."""
    await restore_sensor.async_added_to_hass()
    assert restore_sensor._last_reset == datetime(
        2025, 1, 1, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )
    assert restore_sensor._next_reset == datetime(
        2025, 1, 2, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )
    assert restore_sensor.native_value == 123
    assert restore_sensor.meter.prev_measured_value == 256
    assert restore_sensor._time_window_active is True
    assert restore_sensor._active is False
    assert restore_sensor.sensor_state == SensorState.WAITING_FOR_CONDITION


async def test_added_to_hass_with_restore_old_format(
    restore_sensor_old_format: MeasureItSensor,
) -> None:
    """
    Test sensor restoration with old 'condition_active' field name.

    CRITICAL TEST: This ensures that sensors with data saved using the old
    'condition_active' field name (v0.8.2 and earlier) can successfully
    restore their state after upgrading to v0.8.3/v0.5.1+.

    This prevents catastrophic data loss for sensors that have been measuring
    for extended periods (months or years). Without this migration support,
    all accumulated data would be lost on upgrade.
    """
    await restore_sensor_old_format.async_added_to_hass()

    # Verify the sensor state was fully restored from old format
    assert restore_sensor_old_format._last_reset == datetime(
        2024, 12, 31, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    ), "Last reset time must be preserved"

    assert restore_sensor_old_format._next_reset == datetime(
        2025, 1, 2, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    ), "Next reset time must be preserved"

    assert (
        restore_sensor_old_format.native_value == 8760
    ), "CRITICAL: Measured value (year of data) must be preserved!"

    assert (
        restore_sensor_old_format.meter.prev_measured_value == 8500
    ), "Previous measured value must be preserved"

    assert (
        restore_sensor_old_format._time_window_active is True
    ), "Time window state must be preserved"

    assert (
        restore_sensor_old_format._active is True
    ), "Active state must be migrated from 'condition_active' field"

    assert (
        restore_sensor_old_format.sensor_state == SensorState.MEASURING
    ), "Sensor should be in MEASURING state (both active and time_window_active)"


def test_extra_restore_state_data_property(day_sensor: MeasureItSensor) -> None:
    """Test getting extra restore state data."""
    day_sensor.meter = SourceMeter()
    day_sensor.meter.update(100)
    day_sensor.on_condition_template_change(active=True)
    day_sensor.on_time_window_change(active=True)
    day_sensor.on_value_change(200)
    stored_data = day_sensor.extra_restore_state_data
    assert stored_data.meter_data["measured_value"] == "100"
    assert stored_data.active is True
    assert stored_data.time_window_active is True
    day_sensor.on_condition_template_change(active=False)
    stored_data = day_sensor.extra_restore_state_data
    assert stored_data.active is False


@pytest.mark.parametrize(
    ("input_dt", "expected_dt", "tz", "cron"),
    [
        (
            datetime(2024, 2, 2, 4, 0, tzinfo=ZoneInfo("America/Los_Angeles")),
            datetime(2024, 3, 1, 0, 0, tzinfo=ZoneInfo("America/Los_Angeles")),
            ZoneInfo("America/Los_Angeles"),
            PREDEFINED_PERIODS["month"],
        ),
        (
            datetime(2024, 3, 2, 4, 0, tzinfo=ZoneInfo("America/Los_Angeles")),
            datetime(2024, 4, 1, 0, 0, tzinfo=ZoneInfo("America/Los_Angeles")),
            ZoneInfo("America/Los_Angeles"),
            PREDEFINED_PERIODS["month"],
        ),  # start DST
        (
            datetime(2024, 11, 2, 4, 0, tzinfo=ZoneInfo("America/Los_Angeles")),
            datetime(2024, 12, 1, 0, 0, tzinfo=ZoneInfo("America/Los_Angeles")),
            ZoneInfo("America/Los_Angeles"),
            PREDEFINED_PERIODS["month"],
        ),  # end DST
        (
            datetime(2024, 2, 2, 4, 0, tzinfo=ZoneInfo("Europe/Brussels")),
            datetime(2024, 3, 1, 0, 0, tzinfo=ZoneInfo("Europe/Brussels")),
            ZoneInfo("Europe/Brussels"),
            PREDEFINED_PERIODS["month"],
        ),
        (
            datetime(2024, 3, 2, 4, 0, tzinfo=ZoneInfo("Europe/Brussels")),
            datetime(2024, 4, 1, 0, 0, tzinfo=ZoneInfo("Europe/Brussels")),
            ZoneInfo("Europe/Brussels"),
            PREDEFINED_PERIODS["month"],
        ),  # start DST
        (
            datetime(2024, 3, 10, 1, 0, tzinfo=ZoneInfo("America/Los_Angeles")),
            datetime(2024, 3, 10, 3, 0, tzinfo=ZoneInfo("America/Los_Angeles")),
            ZoneInfo("America/Los_Angeles"),
            PREDEFINED_PERIODS["hour"],
        ),
        (
            datetime(2024, 11, 3, 1, 0, tzinfo=ZoneInfo("America/Los_Angeles")),
            datetime(2024, 11, 3, 2, 0, tzinfo=ZoneInfo("America/Los_Angeles")),
            ZoneInfo("America/Los_Angeles"),
            PREDEFINED_PERIODS["hour"],
        ),
        (
            datetime(2024, 11, 3, 2, 0, tzinfo=ZoneInfo("America/Los_Angeles")),
            datetime(2024, 11, 3, 3, 0, tzinfo=ZoneInfo("America/Los_Angeles")),
            ZoneInfo("America/Los_Angeles"),
            PREDEFINED_PERIODS["hour"],
        ),
        (
            datetime(2024, 2, 2, 4, 0, tzinfo=ZoneInfo("Europe/Brussels")),
            datetime(2024, 2, 2, 5, 0, tzinfo=ZoneInfo("Europe/Brussels")),
            ZoneInfo("Europe/Brussels"),
            PREDEFINED_PERIODS["hour"],
        ),
        (
            datetime(2024, 3, 31, 1, 0, tzinfo=ZoneInfo("Europe/Brussels")),
            datetime(2024, 3, 31, 3, 0, tzinfo=ZoneInfo("Europe/Brussels")),
            ZoneInfo("Europe/Brussels"),
            PREDEFINED_PERIODS["hour"],
        ),
        (
            datetime(2024, 3, 31, 3, 0, tzinfo=ZoneInfo("Europe/Brussels")),
            datetime(2024, 3, 31, 4, 0, tzinfo=ZoneInfo("Europe/Brussels")),
            ZoneInfo("Europe/Brussels"),
            PREDEFINED_PERIODS["hour"],
        ),
        (
            datetime(2024, 10, 26, 1, 0, tzinfo=ZoneInfo("Europe/Brussels")),
            datetime(2024, 10, 26, 2, 0, tzinfo=ZoneInfo("Europe/Brussels")),
            ZoneInfo("Europe/Brussels"),
            PREDEFINED_PERIODS["hour"],
        ),
        (
            datetime(2024, 10, 26, 2, 0, tzinfo=ZoneInfo("Europe/Brussels")),
            datetime(2024, 10, 26, 3, 0, tzinfo=ZoneInfo("Europe/Brussels")),
            ZoneInfo("Europe/Brussels"),
            PREDEFINED_PERIODS["hour"],
        ),
        (
            datetime(2024, 10, 26, 3, 0, tzinfo=ZoneInfo("Europe/Brussels")),
            datetime(2024, 10, 26, 4, 0, tzinfo=ZoneInfo("Europe/Brussels")),
            ZoneInfo("Europe/Brussels"),
            PREDEFINED_PERIODS["hour"],
        ),
    ],
)
def test_next_reset_with_dst(
    hass: HomeAssistant,
    input_dt: datetime,
    expected_dt: datetime,
    tz: ZoneInfo,
    cron: str,
) -> None:
    """Test next reset for hour period with DST."""
    with mock.patch(
        "homeassistant.helpers.condition.dt_util.now",
        return_value=input_dt,
    ):
        dt_util.DEFAULT_TIME_ZONE = tz
        sensor = MeasureItSensor(
            hass,
            MagicMock(),
            CounterMeter(),
            "test_sensor_hour",
            "test_sensor_hour",
            cron,
            lambda x: x,
            SensorStateClass.TOTAL,
        )
        assert sensor._next_reset is None

        sensor.schedule_next_reset()
        assert sensor._next_reset == expected_dt
        sensor.unsub_reset_listener()


# =============================================================================
# COMPREHENSIVE DATA RESTORATION TESTS
# These tests ensure data integrity under all scenarios, including edge cases
# =============================================================================


def test_restore_with_missing_time_window_active_field() -> None:
    """
    Test restoration raises exception when time_window_active is missing.

    DESIRED BEHAVIOR: When required fields are missing (abnormal situation
    indicating data corruption), raise ValueError so the user knows there's
    a problem that needs investigation.

    The exception is caught upstream and logged, allowing the sensor to start
    fresh while alerting the user to check their database.
    """
    data_missing_field = {
        "meter_data": {
            "measured_value": 100.0,
            "prev_measured_value": 90.0,
            "measuring": True,
        },
        "last_reset": "2025-01-01T00:00:00-08:00",
        "next_reset": "2025-02-01T00:00:00-08:00",
        # Missing: time_window_active (abnormal - indicates corruption)
        "active": True,
    }

    with pytest.raises(ValueError, match=r"time_window_active.*missing"):
        MeasureItSensorStoredData.from_dict(data_missing_field)


def test_restore_with_null_datetime_fields() -> None:
    """
    Test restoration handles null datetime fields correctly.

    Sensors may have null last_reset or next_reset in certain states
    (e.g., never reset, or no scheduled reset).
    """
    data_with_nulls = {
        "meter_data": {
            "measured_value": 50.0,
            "prev_measured_value": 40.0,
            "measuring": False,
        },
        "last_reset": None,
        "next_reset": None,
        "time_window_active": False,
        "active": False,
    }
    restored = MeasureItSensorStoredData.from_dict(data_with_nulls)
    assert restored is not None
    assert restored.last_reset is None
    assert restored.next_reset is None
    assert restored.time_window_active is False
    assert restored.active is False


def test_restore_round_trip_preserves_data() -> None:
    """
    Test that data survives a complete save/restore cycle.

    CRITICAL: Ensures no data is lost during serialization and deserialization.
    This tests the complete as_dict() -> from_dict() cycle.
    """
    # Create original data with all fields populated
    original = MeasureItSensorStoredData(
        meter_data={
            "measured_value": 12345.67,
            "prev_measured_value": 11111.11,
            "measuring": True,
            "session_start_value": 10000.0,
        },
        time_window_active=True,
        active=True,
        last_reset=datetime(2024, 6, 15, 12, 30, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE),
        next_reset=datetime(2024, 7, 1, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE),
    )

    # Serialize to dict
    serialized = original.as_dict()

    # Deserialize back
    restored = MeasureItSensorStoredData.from_dict(serialized)

    # Verify all data is preserved
    assert restored is not None, "CRITICAL: Restoration must not return None!"
    assert restored.meter_data == original.meter_data
    assert restored.time_window_active == original.time_window_active
    assert restored.active == original.active
    assert restored.last_reset == original.last_reset
    assert restored.next_reset == original.next_reset


def test_restore_with_invalid_datetime_format() -> None:
    """
    Test restoration raises exception for invalid datetime formats.

    DESIRED BEHAVIOR: Invalid datetime format indicates data corruption or
    database issues. Raise ValueError so the user is alerted to fix the problem.

    The exception is caught upstream, logged with details, and sensor starts fresh.
    """
    data_with_invalid_datetime = {
        "meter_data": {
            "measured_value": 100.0,
            "prev_measured_value": 90.0,
            "measuring": True,
        },
        "last_reset": "not-a-valid-datetime",  # Invalid format
        "next_reset": "2025-02-01T00:00:00-08:00",
        "time_window_active": True,
        "active": True,
    }

    with pytest.raises(ValueError, match=r"Invalid.*last_reset.*datetime"):
        MeasureItSensorStoredData.from_dict(data_with_invalid_datetime)


def test_restore_empty_meter_data() -> None:
    """
    Test restoration with empty meter_data dict.

    DESIRED BEHAVIOR: Empty meter_data is abnormal and indicates corruption.
    Falls back to old format parsing, which will fail and return None.
    This is correct - sensor starts fresh rather than with invalid data.
    """
    data_with_empty_meter_data = {
        "meter_data": {},
        "last_reset": "2025-01-01T00:00:00-08:00",
        "next_reset": "2025-02-01T00:00:00-08:00",
        "time_window_active": True,
        "active": False,
    }
    # Empty meter_data dict evaluates to False, triggers old format fallback
    # Old format expects different fields, so returns None
    restored = MeasureItSensorStoredData.from_dict(data_with_empty_meter_data)
    assert restored is None, "Empty meter_data should return None (corruption)"


def test_restore_all_boolean_combinations() -> None:
    """
    Test restoration with all combinations of active/time_window_active.

    Ensures all four sensor states can be correctly restored:
    1. MEASURING (active=True, time_window=True)
    2. WAITING_FOR_CONDITION (active=False, time_window=True)
    3. WAITING_FOR_TIME_WINDOW (active=True/False, time_window=False)
    """
    test_cases = [
        (True, True, "MEASURING state"),
        (False, True, "WAITING_FOR_CONDITION state"),
        (True, False, "WAITING_FOR_TIME_WINDOW state"),
        (False, False, "WAITING_FOR_TIME_WINDOW state (both inactive)"),
    ]

    for active, time_window_active, description in test_cases:
        data = {
            "meter_data": {
                "measured_value": 100.0,
                "prev_measured_value": 90.0,
                "measuring": active and time_window_active,
            },
            "last_reset": "2025-01-01T00:00:00-08:00",
            "next_reset": "2025-02-01T00:00:00-08:00",
            "time_window_active": time_window_active,
            "active": active,
        }
        restored = MeasureItSensorStoredData.from_dict(data)
        assert restored is not None, f"Failed to restore {description}"
        assert restored.active == active, f"Active state wrong for {description}"
        assert (
            restored.time_window_active == time_window_active
        ), f"Time window state wrong for {description}"


def test_restore_large_measured_values() -> None:
    """
    Test restoration with very large measured values.

    Ensures sensors measuring for years don't overflow or lose precision.
    """
    # Simulate 10 years of continuous measurement (87,600 hours)
    data_large_value = {
        "meter_data": {
            "measured_value": 87600.123456789,
            "prev_measured_value": 87000.987654321,
            "measuring": True,
        },
        "last_reset": "2015-01-01T00:00:00-08:00",
        "next_reset": "2025-01-01T00:00:00-08:00",
        "time_window_active": True,
        "active": True,
    }
    restored = MeasureItSensorStoredData.from_dict(data_large_value)
    assert restored is not None, "CRITICAL: Must handle large values!"
    assert (
        restored.meter_data["measured_value"] == 87600.123456789
    ), "Must preserve precision for large values"
    assert restored.meter_data["prev_measured_value"] == 87000.987654321
