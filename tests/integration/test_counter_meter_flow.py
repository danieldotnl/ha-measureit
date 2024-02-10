"""Test counter meter flow."""

from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.core import HomeAssistant
from custom_components.measureit.const import DOMAIN
from tests import setup_with_mock_config

COUNTER_ENTRY = MockConfigEntry(
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
                "unit_of_measurement": "s",
                "device_class": "duration",
                "state_class": "total_increasing",
                "unique_id": "ca0fce86-b6bb-11ee-923e-0242ac110002",
                "sensor_name": "hour",
                "cron": "0 * * * *",
                "period": "hour",
            },
            {
                "unit_of_measurement": "s",
                "device_class": "duration",
                "state_class": "total_increasing",
                "unique_id": "ca100892-b6bb-11ee-923e-0242ac110002",
                "sensor_name": "day",
                "cron": "0 0 * * *",
                "period": "day",
            },
            {
                "unit_of_measurement": "s",
                "device_class": "duration",
                "state_class": "total_increasing",
                "unique_id": "ca1009aa-b6bb-11ee-923e-0242ac110002",
                "sensor_name": "week",
                "cron": "0 0 * * 1",
                "period": "week",
            },
        ],
    },
)


async def test_counter_meter_setup(hass: HomeAssistant):
    """Test MeasureIt setup."""

    await setup_with_mock_config(hass, COUNTER_ENTRY)

    expected_sensors = ["sensor.test_hour", "sensor.test_day", "sensor.test_week"]
    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "0"
        assert state.attributes["unit_of_measurement"] == "s"
        assert state.attributes["device_class"] == "duration"
        assert state.attributes["state_class"] == "total_increasing"


async def test_counter_meter_counting(hass: HomeAssistant):
    """Test counter_meter should be counting when condition becomes True."""
    # counter_template = "{{ states('sensor.test_counter') | float % 2 == 0 }}"

    hass.states.async_set("sensor.test_counter", "3")
    # sensor.async_schedule_update_ha_state(True)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.test_counter").state == "3"
    await setup_with_mock_config(hass, COUNTER_ENTRY)

    expected_sensors = ["sensor.test_hour", "sensor.test_day", "sensor.test_week"]
    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "0"

    hass.states.async_set("sensor.test_counter", "6")
    await hass.async_block_till_done()

    expected_sensors = ["sensor.test_hour", "sensor.test_day", "sensor.test_week"]
    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "1"

    hass.states.async_set("sensor.test_counter", "7")
    await hass.async_block_till_done()

    expected_sensors = ["sensor.test_hour", "sensor.test_day", "sensor.test_week"]
    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "1"
