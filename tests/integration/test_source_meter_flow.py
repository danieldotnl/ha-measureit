"""Test source meter flow."""

from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.core import HomeAssistant
from custom_components.measureit.const import DOMAIN, SensorState

from tests import setup_with_mock_config, unload_with_mock_config

SOURCE_ENTRY = MockConfigEntry(
    domain=DOMAIN,
    options={
        "config_name": "test",
        "meter_type": "source",
        "condition": "{{ is_state('switch.test_switch', 'on') }}",
        "when_days": ["0", "1", "2", "3", "4", "5", "6"],
        "source_entity": "sensor.test_source",
        "when_from": "00:00:00",
        "when_till": "00:00:00",
        "sensor": [
            {
                "unit_of_measurement": "items",
                "state_class": "total",
                "unique_id": "ca0fce86-b6bb-11ee-923e-0242ac110002",
                "sensor_name": "hour",
                "cron": "0 * * * *",
                "period": "hour",
            },
            {
                "unit_of_measurement": "items",
                "state_class": "total",
                "unique_id": "ca100892-b6bb-11ee-923e-0242ac110002",
                "sensor_name": "day",
                "cron": "0 0 * * *",
                "period": "day",
            },
            {
                "unit_of_measurement": "items",
                "state_class": "total",
                "unique_id": "ca1009aa-b6bb-11ee-923e-0242ac110002",
                "sensor_name": "week",
                "cron": "0 0 * * 1",
                "period": "week",
            },
        ],
    },
)


async def test_source_meter_setup(hass: HomeAssistant):
    """Test MeasureIt setup for source meter."""
    hass.states.async_set("sensor.test_source", "3")
    hass.states.async_set("switch.test_switch", "off")
    await hass.async_block_till_done()

    await setup_with_mock_config(hass, SOURCE_ENTRY)

    expected_sensors = ["sensor.test_hour", "sensor.test_day", "sensor.test_week"]
    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "0"
        assert state.attributes["unit_of_measurement"] == "items"
        assert state.attributes.get("device_class") is None
        assert state.attributes["state_class"] == "total"
        assert state.attributes["status"] == SensorState.WAITING_FOR_CONDITION

    hass.states.async_set("switch.test_switch", "on")
    await hass.async_block_till_done()

    expected_sensors = ["sensor.test_hour", "sensor.test_day", "sensor.test_week"]
    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state.attributes["status"] == SensorState.MEASURING

    await unload_with_mock_config(hass, SOURCE_ENTRY)


async def test_source_meter_measuring(hass: HomeAssistant):
    """Test counter_meter should be counting when condition becomes True."""

    hass.states.async_set("sensor.test_source", "3")
    hass.states.async_set("switch.test_switch", "on")
    await hass.async_block_till_done()
    assert hass.states.get("sensor.test_source").state == "3"
    await setup_with_mock_config(hass, SOURCE_ENTRY)

    expected_sensors = ["sensor.test_hour", "sensor.test_day", "sensor.test_week"]
    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "0"

    hass.states.async_set("sensor.test_source", "6")
    await hass.async_block_till_done()

    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "3"

    hass.states.async_set("sensor.test_source", "7")
    await hass.async_block_till_done()

    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "4"

    hass.states.async_set("sensor.test_source", "8")
    await hass.async_block_till_done()

    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "5"

    hass.states.async_set("sensor.test_source", "50")
    await hass.async_block_till_done()

    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "47"

    hass.states.async_set("sensor.test_source", "40")
    await hass.async_block_till_done()

    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "37"

    await unload_with_mock_config(hass, SOURCE_ENTRY)


async def test_continue_after_reload(hass: HomeAssistant):
    """Test counter_meter should be counting when condition becomes True."""

    hass.states.async_set("sensor.test_source", "3")
    hass.states.async_set("switch.test_switch", "on")
    await hass.async_block_till_done()
    assert hass.states.get("sensor.test_source").state == "3"
    await setup_with_mock_config(hass, SOURCE_ENTRY)

    expected_sensors = ["sensor.test_hour", "sensor.test_day", "sensor.test_week"]
    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "0"

    hass.states.async_set("sensor.test_source", "6")
    await hass.async_block_till_done()

    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "3"

    await unload_with_mock_config(hass, SOURCE_ENTRY)
    await setup_with_mock_config(hass, SOURCE_ENTRY)

    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "3"

    hass.states.async_set("sensor.test_source", "7")
    await hass.async_block_till_done()

    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "4"

    await unload_with_mock_config(hass, SOURCE_ENTRY)
    hass.states.async_set("sensor.test_source", "10")
    await hass.async_block_till_done()
    await setup_with_mock_config(hass, SOURCE_ENTRY)

    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "7"

    hass.states.async_set("sensor.test_source", "20")
    await hass.async_block_till_done()

    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "17"


async def test_continue_after_condition_change(hass: HomeAssistant):
    """Test counter_meter should be counting when condition becomes True."""

    hass.states.async_set("sensor.test_source", "3")
    hass.states.async_set("switch.test_switch", "on")
    await hass.async_block_till_done()
    assert hass.states.get("sensor.test_source").state == "3"
    await setup_with_mock_config(hass, SOURCE_ENTRY)

    sensor = "sensor.test_day"
    state = hass.states.get(sensor)
    assert state.state == "0"

    hass.states.async_set("sensor.test_source", "6")
    await hass.async_block_till_done()

    state = hass.states.get(sensor)
    assert state.state == "3"

    hass.states.async_set("switch.test_switch", "off")
    await hass.async_block_till_done()

    # condition becomes false during restart
    await unload_with_mock_config(hass, SOURCE_ENTRY)
    hass.states.async_set("sensor.test_source", "10")
    await hass.async_block_till_done()
    await setup_with_mock_config(hass, SOURCE_ENTRY)

    state = hass.states.get(sensor)
    assert state.attributes["status"] == SensorState.WAITING_FOR_CONDITION
    assert state.state == "3"

    hass.states.async_set("switch.test_switch", "on")
    hass.states.async_set("sensor.test_source", "17")
    await hass.async_block_till_done()

    state = hass.states.get(sensor)
    assert state.state == "10"

    # condition stay true while restarting
    await unload_with_mock_config(hass, SOURCE_ENTRY)
    hass.states.async_set("sensor.test_source", "20")
    await hass.async_block_till_done()
    await setup_with_mock_config(hass, SOURCE_ENTRY)

    state = hass.states.get(sensor)
    assert state.state == "13"


async def test_reset(hass: HomeAssistant):
    """Test counter_meter reset."""

    hass.states.async_set("sensor.test_source", "3")
    hass.states.async_set("switch.test_switch", "on")
    await hass.async_block_till_done()
    assert hass.states.get("sensor.test_source").state == "3"
    await setup_with_mock_config(hass, SOURCE_ENTRY)

    sensor = "sensor.test_day"
    state = hass.states.get(sensor)
    assert state.state == "0"

    hass.states.async_set("sensor.test_source", "6")
    await hass.async_block_till_done()

    state = hass.states.get(sensor)
    assert state.state == "3"

    await hass.services.async_call("measureit", "reset", {"entity_id": sensor})
    await hass.async_block_till_done()

    state = hass.states.get(sensor)
    assert state.state == "0"
    assert state.attributes["prev_period"] == "3"

    sensor = "sensor.test_hour"
    state = hass.states.get(sensor)
    assert state.state == "3"
    assert state.attributes["prev_period"] == "0"

    await unload_with_mock_config(hass, SOURCE_ENTRY)
    await hass.async_block_till_done()
