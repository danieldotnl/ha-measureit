"""Test counter meter flow."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

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
                "unique_id": "ca100892-b6bb-11ee-923e-0242ac110002",
                "sensor_name": "day",
                "cron": "0 0 * * *",
                "period": "day",
            },
            {
                "unit_of_measurement": "s",
                "device_class": "duration",
                "state_class": "total",
                "unique_id": "ca1009aa-b6bb-11ee-923e-0242ac110002",
                "sensor_name": "week",
                "cron": "0 0 * * 1",
                "period": "week",
            },
        ],
    },
)


async def test_counter_meter_setup(hass: HomeAssistant) -> None:
    """Test MeasureIt setup."""
    await setup_with_mock_config(hass, COUNTER_ENTRY)

    expected_sensors = ["sensor.test_hour", "sensor.test_day", "sensor.test_week"]
    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "0"
        assert state.attributes["unit_of_measurement"] == "s"
        assert state.attributes["device_class"] == "duration"
        assert state.attributes["state_class"] == "total"


async def test_counter_meter_counting(hass: HomeAssistant) -> None:
    """Test counter_meter should be counting when condition becomes True."""
    # counter_template = "{{ states('sensor.test_counter') | float % 2 == 0 }}"

    hass.states.async_set("sensor.test_counter", "3")
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

    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "1"

    hass.states.async_set("sensor.test_counter", "7")
    await hass.async_block_till_done()

    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "1"

    hass.states.async_set("sensor.test_counter", "8")
    await hass.async_block_till_done()

    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "2"

    hass.states.async_set("sensor.test_counter", "10")
    await hass.async_block_till_done()
    # THIS DOES NOT UPDATE THE SENSOR SINCE THE VALUE OF THE TEMPLATE DOESN'T CHANGE,
    # IT WAS AND STAYS TRUE SO IT DOES NOT TRIGGER

    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "2"


async def test_counter_should_not_count_positive_template_on_startup(
    hass: HomeAssistant,
) -> None:
    """Test counter_meter should be counting when condition becomes True."""
    # counter_template = "{{ states('sensor.test_counter') | float % 2 == 0 }}"

    hass.states.async_set("sensor.test_counter", "4")
    await hass.async_block_till_done()
    assert hass.states.get("sensor.test_counter").state == "4"
    await setup_with_mock_config(hass, COUNTER_ENTRY)

    expected_sensors = ["sensor.test_hour", "sensor.test_day", "sensor.test_week"]
    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "0"

    hass.states.async_set("sensor.test_counter", "6")
    await hass.async_block_till_done()

    for entity_id in expected_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "1"


async def test_counter_calibrate(hass: HomeAssistant) -> None:
    """Test calibration of counter meter."""
    # counter_template = "{{ states('sensor.test_counter') | float % 2 == 0 }}"

    hass.states.async_set("sensor.test_counter", "3")
    await hass.async_block_till_done()
    assert hass.states.get("sensor.test_counter").state == "3"
    await setup_with_mock_config(hass, COUNTER_ENTRY)

    sensor = "sensor.test_day"
    other_sensors = ["sensor.test_hour", "sensor.test_week"]

    state = hass.states.get(sensor)
    assert state.state == "0"
    for entity_id in other_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "0"

    hass.states.async_set("sensor.test_counter", "6")
    await hass.async_block_till_done()

    state = hass.states.get(sensor)
    assert state.state == "1"
    for entity_id in other_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "1"

    await hass.services.async_call(
        DOMAIN, "calibrate", {"entity_id": sensor, "value": 100}
    )
    await hass.async_block_till_done()

    state = hass.states.get(sensor)
    assert state.state == "100"
    for entity_id in other_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "1"

    # template needs to be come false so it will trigger again
    hass.states.async_set("sensor.test_counter", "7")
    await hass.async_block_till_done()

    hass.states.async_set("sensor.test_counter", "8")
    await hass.async_block_till_done()

    state = hass.states.get(sensor)
    assert state.state == "101"
    for entity_id in other_sensors:
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "2"
