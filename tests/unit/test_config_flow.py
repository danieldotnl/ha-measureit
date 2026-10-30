"""Tests for MeasureIt config_flow class."""

from unittest.mock import patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_DEVICE_ID,
    CONF_UNIT_OF_MEASUREMENT,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.measureit.const import (
    CONF_CONDITION,
    CONF_CONFIG_NAME,
    CONF_COUNTER_TEMPLATE,
    CONF_PERIODS,
    CONF_SOURCE,
    CONF_STATE_CLASS,
    CONF_TW_DAYS,
    CONF_TW_FROM,
    CONF_TW_TILL,
    DOMAIN,
)


# This fixture bypasses the actual setup of the integration
# since we only want to test the config flow. We test the
# actual functionality of the integration in other test modules.
@pytest.fixture(autouse=True)
def bypass_setup_fixture():
    """Prevent setup."""
    with patch(
        "custom_components.measureit.async_setup_entry",
        return_value=True,
    ):
        yield


async def test_counter_config_flow(hass: HomeAssistant) -> None:
    """Test the config flow for setting up a config with counter meters."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Check that the config flow shows the menu as the first step
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "user"

    # Choose config for a time config
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "count"}
    )

    # Check that the config flow shows the form for the config name
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    # Fill config name
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_CONFIG_NAME: "test_config_counter",
            CONF_COUNTER_TEMPLATE: "{{ True }}",
        },
    )

    assert result["errors"] is None
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "when"

    # Fill the when config step
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_CONDITION: "{{ is_state('binary_sensor.test_sensor', 'on') }}",
            CONF_TW_DAYS: ["1", "2", "3"],
            CONF_TW_FROM: "00:00",
            CONF_TW_TILL: "00:00",
        },
    )

    assert result["errors"] is None
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "sensors"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_PERIODS: ["day", "week", "noreset"],
            CONF_UNIT_OF_MEASUREMENT: "clicks",
        },
    )

    assert result["errors"] is None
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "thank_you"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY

    config_entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert config_entry.data == {}
    assert config_entry.options.get(CONF_CONFIG_NAME) == "test_config_counter"
    assert config_entry.options.get(CONF_COUNTER_TEMPLATE) == "{{ True }}"
    assert config_entry.title == "test_config_counter"


async def test_time_config_flow(hass: HomeAssistant) -> None:
    """Test the config flow for setting up a config with time meters."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Check that the config flow shows the menu as the first step
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "user"

    # Choose config for a time config
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "time"}
    )

    # Check that the config flow shows the form for the config name
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    # Fill config name
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_CONFIG_NAME: "test_config_time"}
    )

    assert result["errors"] is None
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "when"

    # Fill the when config step
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_CONDITION: "{{ is_state('binary_sensor.test_sensor', 'on') }}",
            CONF_TW_DAYS: ["1", "2", "3"],
            CONF_TW_FROM: "00:00",
            CONF_TW_TILL: "00:00",
        },
    )

    assert result["errors"] is None
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "sensors"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_PERIODS: ["day", "week", "noreset"],
            CONF_UNIT_OF_MEASUREMENT: "s",
            CONF_DEVICE_CLASS: "duration",
            CONF_STATE_CLASS: "total_increasing",
        },
    )

    assert result["errors"] is None
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "thank_you"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_validate_cron(hass: HomeAssistant) -> None:
    """Test validate cron in config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Choose config for a time config
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "time"}
    )

    # Fill config name
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_CONFIG_NAME: "test_config_time"}
    )

    # Fill without valid days
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_CONDITION: "{{ is_state('binary_sensor.test_sensor', 'on') }}",
            CONF_TW_FROM: "00:00",
            CONF_TW_TILL: "00:00",
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_PERIODS: ["123 * * * *"],
            CONF_UNIT_OF_MEASUREMENT: "s",
            CONF_DEVICE_CLASS: "duration",
            CONF_STATE_CLASS: "total_increasing",
        },
    )

    assert result["errors"] == {"base": "invalid_cron"}


async def test_flow_with_errors(hass: HomeAssistant) -> None:
    """Test flow with input that doesn't validate."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Choose config for a time config
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "time"}
    )

    # Fill config name
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_CONFIG_NAME: "test_config_time"}
    )

    # Fill without valid days
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_CONDITION: "{{ is_state('binary_sensor.test_sensor', 'on') }}",
            CONF_TW_DAYS: [],
            CONF_TW_FROM: "00:00",
            CONF_TW_TILL: "00:00",
        },
    )

    assert result["errors"] == {"base": "tw_days_minimum"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_CONDITION: "{{ is_statsdfe('binary_sensor.test_sensor', 'on') }}",
            CONF_TW_DAYS: ["0"],
            CONF_TW_FROM: "00:00",
            CONF_TW_TILL: "00:00",
        },
    )

    assert result["errors"] == {"base": "condition_invalid"}


async def test_source_config_flow(hass: HomeAssistant) -> None:
    """Test the config flow for setting up a config with source meters."""
    # Set up a mock source entity with attributes
    hass.states.async_set(
        "sensor.energy_meter",
        "100.5",
        {"device_class": "energy", "unit_of_measurement": "kWh"},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Check that the config flow shows the menu as the first step
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "user"

    # Choose config for a source config
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "source"}
    )

    # Check that the config flow shows the form for the config name and source
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "source"

    # Fill config name and source entity
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_CONFIG_NAME: "test_config_source",
            CONF_SOURCE: "sensor.energy_meter",
        },
    )

    assert result["errors"] is None
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "when"

    # Fill the when config step
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_TW_DAYS: ["0", "1", "2", "3", "4", "5", "6"],
            CONF_TW_FROM: "00:00",
            CONF_TW_TILL: "00:00",
        },
    )

    # This is where the bug manifests - transitioning to sensors step fails
    # because get_add_sensor_suggested_values always raises ValueError for SOURCE type
    assert result["errors"] is None
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "sensors"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_PERIODS: ["day", "month"],
            CONF_UNIT_OF_MEASUREMENT: "kWh",
            CONF_DEVICE_CLASS: "energy",
            CONF_STATE_CLASS: "total",
        },
    )

    assert result["errors"] is None
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "thank_you"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY

    config_entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert config_entry.data == {}
    assert config_entry.options.get(CONF_CONFIG_NAME) == "test_config_source"
    assert config_entry.options.get(CONF_SOURCE) == "sensor.energy_meter"
    assert CONF_DEVICE_ID not in config_entry.options
    assert config_entry.title == "test_config_source"


async def create_source_entry(
    hass: HomeAssistant, source_input: dict[str, str]
) -> dict:
    """Run the source config flow and return the options of the created entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "source"}
    )
    for user_input in (
        {CONF_CONFIG_NAME: "test_config_source", **source_input},
        {
            CONF_TW_DAYS: ["0", "1", "2", "3", "4", "5", "6"],
            CONF_TW_FROM: "00:00",
            CONF_TW_TILL: "00:00",
        },
        {CONF_PERIODS: ["day"]},
        {},
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=user_input
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    return hass.config_entries.async_entries(DOMAIN)[0].options


def register_source_on_devices(hass: HomeAssistant) -> tuple[str, str]:
    """Register the source entity on a device and create a second device."""
    device_config_entry = MockConfigEntry(domain="test")
    device_config_entry.add_to_hass(hass)
    device_registry = dr.async_get(hass)
    source_device = device_registry.async_get_or_create(
        config_entry_id=device_config_entry.entry_id, identifiers={("test", "source")}
    )
    other_device = device_registry.async_get_or_create(
        config_entry_id=device_config_entry.entry_id, identifiers={("test", "other")}
    )
    er.async_get(hass).async_get_or_create(
        "sensor",
        "test",
        "energy_meter",
        suggested_object_id="energy_meter",
        device_id=source_device.id,
    )
    hass.states.async_set("sensor.energy_meter", "100.5")
    return source_device.id, other_device.id


async def test_source_config_flow_defaults_to_source_device(
    hass: HomeAssistant,
) -> None:
    """Test the device defaults to the device of the source entity."""
    source_device_id, _ = register_source_on_devices(hass)

    options = await create_source_entry(hass, {CONF_SOURCE: "sensor.energy_meter"})

    assert options[CONF_DEVICE_ID] == source_device_id


async def test_source_config_flow_keeps_selected_device(hass: HomeAssistant) -> None:
    """Test a selected device is not replaced by the source entity's device."""
    _, other_device_id = register_source_on_devices(hass)

    options = await create_source_entry(
        hass, {CONF_SOURCE: "sensor.energy_meter", CONF_DEVICE_ID: other_device_id}
    )

    assert options[CONF_DEVICE_ID] == other_device_id
