"""Test source meter flow."""

from datetime import datetime
from decimal import Decimal
from freezegun import freeze_time
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_fire_time_changed_exact,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from custom_components.measureit.const import DOMAIN, SensorState

from tests import setup_with_mock_config, unload_with_mock_config

TIME_ENTRY = MockConfigEntry(
    domain=DOMAIN,
    options={
        "config_name": "test",
        "meter_type": "time",
        "when_days": ["0", "1"],  # Only on Monday and Tuesday
        "when_from": "05:00:00",
        "when_till": "21:00:00",  # Only until 21:00
        "condition": "{{ is_state('switch.test_switch', 'on') }}",
        "sensor": [
            {
                "unit_of_measurement": "s",
                "state_class": "total",
                "device_class": "duration",
                "unique_id": "ca0fce86-b6bb-11ee-923e-0242ac110002",
                "sensor_name": "hour",
                "cron": "0 * * * *",
                "period": "hour",
            },
            {
                "unit_of_measurement": "s",
                "state_class": "total",
                "device_class": "duration",
                "unique_id": "ca100892-b6bb-11ee-923e-0242ac110002",
                "sensor_name": "day",
                "cron": "0 0 * * *",
                "period": "day",
            },
            {
                "unit_of_measurement": "s",
                "state_class": "total",
                "device_class": "duration",
                "unique_id": "ca1009aa-b6bb-11ee-923e-0242ac110002",
                "sensor_name": "week",
                "cron": "0 0 * * 1",
                "period": "week",
            },
        ],
    },
)


async def test_time_meter_setup(hass: HomeAssistant):
    """Test MeasureIt setup for source meter."""
    hass.states.async_set("switch.test_switch", "on")
    await hass.async_block_till_done()

    current_time = datetime(2024, 2, 12, 8, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    with freeze_time(current_time):
        async_fire_time_changed(hass, current_time)
        await hass.async_block_till_done()
        await setup_with_mock_config(hass, TIME_ENTRY)

        expected_sensors = ["sensor.test_hour", "sensor.test_day", "sensor.test_week"]
        for entity_id in expected_sensors:
            state = hass.states.get(entity_id)
            assert state.attributes["status"] == SensorState.MEASURING
            assert state
            assert Decimal(state.state) == 0  # 0 because frozen
            assert state.attributes["unit_of_measurement"] == "s"
            assert state.attributes["device_class"] == "duration"
            assert state.attributes["state_class"] == "total"

    await unload_with_mock_config(hass, TIME_ENTRY)


async def test_time_meter_measuring(hass: HomeAssistant):
    """Test MeasureIt setup for source meter."""
    hass.states.async_set("switch.test_switch", "on")
    await hass.async_block_till_done()

    current_time = datetime(2024, 2, 12, 8, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    with freeze_time(current_time) as mock_time:
        async_fire_time_changed(hass, current_time)
        await hass.async_block_till_done()
        await setup_with_mock_config(hass, TIME_ENTRY)

        expected_sensors = ["sensor.test_hour", "sensor.test_day", "sensor.test_week"]
        for entity_id in expected_sensors:
            state = hass.states.get(entity_id)
            assert state.attributes["status"] == SensorState.MEASURING
            assert state
            assert Decimal(state.state) == 0  # 0 because frozen
            assert state.attributes["unit_of_measurement"] == "s"
            assert state.attributes["device_class"] == "duration"
            assert state.attributes["state_class"] == "total"

        current_time = datetime(2024, 2, 12, 8, 1, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
        mock_time.move_to(current_time)
        async_fire_time_changed(hass, current_time)
        await hass.async_block_till_done()

        state = hass.states.get("sensor.test_hour")
        assert Decimal(state.state) == 60

    await unload_with_mock_config(hass, TIME_ENTRY)


async def test_time_meter_start(hass: HomeAssistant):
    """Test MeasureIt setup for source meter."""
    # "when_days": ["0", "1"],  # Only on Monday and Tuesday
    # "when_from": "00:00:00",
    # "when_till": "21:00:00",

    hass.states.async_set("switch.test_switch", "on")
    await hass.async_block_till_done()

    sensor = "sensor.test_day"
    current_time = datetime(2024, 2, 12, 4, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    with freeze_time(current_time) as mock_time:
        async_fire_time_changed(hass, current_time)
        await hass.async_block_till_done()

        await setup_with_mock_config(hass, TIME_ENTRY)

        state = hass.states.get(sensor)
        assert state.attributes["status"] == SensorState.WAITING_FOR_TIME_WINDOW
        assert Decimal(state.state) == 0  # 0 because frozen

        current_time = datetime(2024, 2, 12, 5, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
        mock_time.move_to(current_time)
        async_fire_time_changed_exact(hass, current_time)

        current_time = datetime(2024, 2, 12, 5, 30, tzinfo=dt_util.DEFAULT_TIME_ZONE)
        mock_time.move_to(current_time)
        async_fire_time_changed_exact(hass, current_time)
        await hass.async_block_till_done()
        state = hass.states.get(sensor)
        assert state.attributes["status"] == SensorState.MEASURING
        assert Decimal(state.state) == 30 * 60


async def test_time_meter_stop(hass: HomeAssistant):
    """Test MeasureIt setup for source meter."""

    hass.states.async_set("switch.test_switch", "on")
    await hass.async_block_till_done()

    sensor = "sensor.test_day"
    current_time = datetime(2024, 2, 12, 19, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    with freeze_time(current_time) as mock_time:
        async_fire_time_changed(hass, current_time)
        await hass.async_block_till_done()

        await setup_with_mock_config(hass, TIME_ENTRY)

        state = hass.states.get(sensor)
        assert state.attributes["status"] == SensorState.MEASURING
        assert Decimal(state.state) == 0  # 0 because frozen

        current_time = datetime(2024, 2, 12, 21, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
        mock_time.move_to(current_time)
        async_fire_time_changed_exact(hass, current_time)
        await hass.async_block_till_done()
        state = hass.states.get(sensor)
        assert state.attributes["status"] == SensorState.WAITING_FOR_TIME_WINDOW
        assert Decimal(state.state) == 2 * 60 * 60

        current_time = datetime(2024, 2, 12, 22, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
        mock_time.move_to(current_time)
        async_fire_time_changed_exact(hass, current_time)
        await hass.async_block_till_done()
        state = hass.states.get(sensor)
        assert state.attributes["status"] == SensorState.WAITING_FOR_TIME_WINDOW
        assert Decimal(state.state) == 2 * 60 * 60


async def test_reset_end_of_period(hass: HomeAssistant):
    """Test if meter resets at end of period."""
    # "when_days": ["0", "1"],  # Only on Monday and Tuesday
    # "when_from": "05:00:00",
    # "when_till": "21:00:00",

    hass.states.async_set("switch.test_switch", "on")
    await hass.async_block_till_done()

    sensor = "sensor.test_day"
    current_time = datetime(2024, 2, 12, 19, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    with freeze_time(current_time) as mock_time:
        async_fire_time_changed(hass, current_time)
        await hass.async_block_till_done()

        await setup_with_mock_config(hass, TIME_ENTRY)

        state = hass.states.get(sensor)
        assert state.attributes["status"] == SensorState.MEASURING
        assert Decimal(state.state) == 0  # 0 because frozen

        current_time = datetime(2024, 2, 12, 21, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
        mock_time.move_to(current_time)
        async_fire_time_changed_exact(hass, current_time)
        await hass.async_block_till_done()
        state = hass.states.get(sensor)
        assert state.attributes["status"] == SensorState.WAITING_FOR_TIME_WINDOW
        assert Decimal(state.state) == 2 * 60 * 60

        current_time = datetime(2024, 2, 13, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
        mock_time.move_to(current_time)
        async_fire_time_changed_exact(hass, current_time)
        await hass.async_block_till_done()
        state = hass.states.get(sensor)
        assert state.attributes["status"] == SensorState.WAITING_FOR_TIME_WINDOW
        assert Decimal(state.state) == 0
        assert Decimal(state.attributes["prev_period"]) == Decimal(2 * 60 * 60)
