"""Tests for MeasureIt sensor class."""
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.measureit import async_setup_entry, async_unload_entry
from custom_components.measureit.const import DOMAIN


async def test_sensor_creation(hass):
    """Test the creation of sensors in Home Assistant."""
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "config_name": "test_config",
            "meter_type": "time",
            "when_days": ["0", "1", "2", "3", "4", "5", "6"],
            "when_from": "00:00:00",
            "when_till": "00:00:00",
            "sensor": [
                {
                    "unit_of_measurement": "s",
                    "device_class": "duration",
                    "state_class": "total_increasing",
                    "unique_id": "50d844d8-b5ff-11ee-8d04-0242ac110002",
                    "sensor_name": "day",
                    "cron": "0 0 * * *",
                    "period": "day",
                },
                {
                    "unit_of_measurement": "s",
                    "device_class": "duration",
                    "state_class": "total_increasing",
                    "unique_id": "50d859e6-b5ff-11ee-8d04-0242ac110002",
                    "sensor_name": "week",
                    "cron": "0 0 * * 1",
                    "period": "week",
                },
            ],
        },
        title="My time config",
    )

    assert await async_setup_entry(hass, config_entry)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_config_day")
    assert state
    state = hass.states.get("sensor.test_config_week")
    assert state

    await async_unload_entry(hass, config_entry)
    await hass.async_block_till_done()
