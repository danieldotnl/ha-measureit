"""Test counter meter flow."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.measureit.const import DOMAIN, SensorState
from tests import setup_with_mock_config, unload_with_mock_config

COUNTER_ENTRY = MockConfigEntry(
    domain=DOMAIN,
    options={
        "config_name": "test",
        "meter_type": "counter",
        "condition": "{{ is_state('switch.test_switch', 'on') }}",
        "when_days": ["0", "1", "2", "3", "4", "5", "6"],
        "counter_template": "{{ states('sensor.test_counter') | float % 2 == 0 }}",
        "when_from": "00:00:00",
        "when_till": "00:00:00",
        "sensor": [
            {
                "unit_of_measurement": "s",
                "device_class": "duration",
                "state_class": "total",
                "unique_id": "ca0fce86-b6bb-11ee-923e-0242ac110002",
                "sensor_name": "hour",
                "cron": "0 * * * *",
                "period": "hour",
            },
            {
                "unit_of_measurement": "s",
                "device_class": "duration",
                "state_class": "total",
                "unique_id": "ca0fce86-b6bb-11ee-923e-0242ac110003",
                "sensor_name": "day",
                "cron": "0 * * * *",
                "period": "day",
                "value_template": "{{ value * 3 }}",
            },
        ],
    },
)


async def test_value_template_applied(hass: HomeAssistant):
    """Test value_template is applied."""
    hass.states.async_set("sensor.test_counter", "4")
    hass.states.async_set("switch.test_switch", "on")
    await hass.async_block_till_done()
    assert hass.states.get("sensor.test_counter").state == "4"
    assert hass.states.get("switch.test_switch").state == "on"
    await setup_with_mock_config(hass, COUNTER_ENTRY)

    state = hass.states.get("sensor.test_day")
    assert state.state == "0"

    hass.states.async_set("sensor.test_counter", "6")
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_day")
    # check if value_template is applied: value_template: "{{ value * 3 }}"
    assert state.state == "3"

    hass.states.async_set("sensor.test_counter", "7")
    await hass.async_block_till_done()
    hass.states.async_set("sensor.test_counter", "8")
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_day")
    assert state.state == "6"


async def test_only_counting_when_condition_met_start_true_and_value_template_applied(
    hass: HomeAssistant,
):
    """Test counter_meter should be counting when condition becomes True."""
    # counter_template = "{{ states('sensor.test_counter') | float % 2 == 0 }}"

    hass.states.async_set("sensor.test_counter", "4")
    hass.states.async_set("switch.test_switch", "on")
    await hass.async_block_till_done()
    assert hass.states.get("sensor.test_counter").state == "4"
    assert hass.states.get("switch.test_switch").state == "on"
    await setup_with_mock_config(hass, COUNTER_ENTRY)

    expected_sensors = ["sensor.test_hour"]
    state = hass.states.get("sensor.test_hour")
    assert state.state == "0"

    hass.states.async_set("sensor.test_counter", "6")
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_hour")
    assert state.state == "1"

    hass.states.async_set("switch.test_switch", "off")
    await hass.async_block_till_done()

    hass.states.async_set("sensor.test_counter", "8")
    await hass.async_block_till_done()

    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "1"

    await unload_with_mock_config(hass, COUNTER_ENTRY)


async def test_only_counting_when_condition_met_start_false(hass: HomeAssistant):
    """Test counter_meter should be counting when condition becomes True."""
    # counter_template = "{{ states('sensor.test_counter') | float % 2 == 0 }}"

    hass.states.async_set("sensor.test_counter", "4")
    hass.states.async_set("switch.test_switch", "off")
    await hass.async_block_till_done()
    assert hass.states.get("sensor.test_counter").state == "4"
    assert hass.states.get("switch.test_switch").state == "off"
    await setup_with_mock_config(hass, COUNTER_ENTRY)

    expected_sensors = ["sensor.test_hour"]
    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "0"

    hass.states.async_set("sensor.test_counter", "6")
    await hass.async_block_till_done()

    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "0"

    hass.states.async_set("switch.test_switch", "on")
    await hass.async_block_till_done()

    hass.states.async_set("sensor.test_counter", "11")
    await hass.async_block_till_done()

    hass.states.async_set("sensor.test_counter", "8")
    await hass.async_block_till_done()

    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "1"

    await unload_with_mock_config(hass, COUNTER_ENTRY)

async def test_continue_after_condition_entity_unavailable(
    hass: HomeAssistant,
):
    """Test counter_meter should be counting when condition becomes True."""
    # counter_template = "{{ states('sensor.test_counter') | float % 2 == 0 }}"

    hass.states.async_set("sensor.test_counter", "4")
    #hass.states.async_set("switch.test_switch", "on")
    await hass.async_block_till_done()
    assert hass.states.get("sensor.test_counter").state == "4"
    #assert hass.states.get("switch.test_switch").state == "on"
    await setup_with_mock_config(hass, COUNTER_ENTRY)

    expected_sensors = ["sensor.test_hour"]
    state = hass.states.get("sensor.test_hour")
    assert state.state == "0"
    assert state.attributes.get("status") == SensorState.WAITING_FOR_CONDITION

    hass.states.async_set("sensor.test_counter", "6")
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_hour")
    assert state.state == "0" # because the condition is not met

    hass.states.async_set("switch.test_switch", "on")
    await hass.async_block_till_done()
    state = hass.states.get("sensor.test_hour")
    assert state.attributes.get("status") == SensorState.MEASURING

    hass.states.async_set("sensor.test_counter", "9")
    await hass.async_block_till_done()
    hass.states.async_set("sensor.test_counter", "10")
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_hour")
    assert state.state == "1"

    hass.states.async_set("switch.test_switch", "off")
    await hass.async_block_till_done()

    hass.states.async_set("sensor.test_counter", "8")
    await hass.async_block_till_done()

    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "1"

    await unload_with_mock_config(hass, COUNTER_ENTRY)
