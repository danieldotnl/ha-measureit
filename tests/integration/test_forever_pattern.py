"""Tests for sensors with a noreset pattern."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.measureit.const import DOMAIN
from tests import setup_with_mock_config, unload_with_mock_config

FOREVER_ENTRY = MockConfigEntry(
    domain=DOMAIN,
    options={
        "config_name": "test",
        "meter_type": "counter",
        "when_days": ["0", "1", "2", "3", "4", "5", "6"],
        "counter_template": "{{ states('sensor.test_counter') | float % 2 == 0 }}",
        "when_from": "00:00:00",
        "when_till": "00:00:00",
        "sensor": [
            {
                "unit_of_measurement": "counts",
                "state_class": "total",
                "unique_id": "ca0fce86-b6bb-11ee-923e-0242ac110002",
                "sensor_name": "noreset",
                "cron": "noreset",
                "period": "noreset",
            },
        ],
    },
)


async def test_noreset_meter_setup(hass: HomeAssistant) -> None:
    """Test MeasureIt setup."""
    await setup_with_mock_config(hass, FOREVER_ENTRY)

    sensor = "sensor.test_noreset"
    state = hass.states.get(sensor)
    assert state.state == "0"
    assert state.attributes.get("sensor_last_reset") is not None
    assert state.attributes["sensor_next_reset"] is None
    assert state.attributes["unit_of_measurement"] == "counts"
    assert state.attributes["state_class"] == "total"

    await unload_with_mock_config(hass, FOREVER_ENTRY)


async def test_noreset_meter_reset(hass: HomeAssistant) -> None:
    """Test MeasureIt reset."""
    hass.states.async_set("sensor.test_counter", "3")
    await hass.async_block_till_done()

    await setup_with_mock_config(hass, FOREVER_ENTRY)

    sensor = "sensor.test_noreset"
    state = hass.states.get(sensor)
    assert state.state == "0"

    hass.states.async_set("sensor.test_counter", "4")
    await hass.async_block_till_done()

    state = hass.states.get(sensor)
    assert state.state == "1"

    await hass.services.async_call(DOMAIN, "reset", {"entity_id": sensor})
    await hass.async_block_till_done()

    state = hass.states.get(sensor)
    assert state.state == "0"
    assert state.attributes["sensor_next_reset"] is None
    assert state.attributes["sensor_last_reset"] is not None
    assert state.attributes["last_reset"] is not None
    assert state.attributes["prev_period"] == "1"

    await unload_with_mock_config(hass, FOREVER_ENTRY)
