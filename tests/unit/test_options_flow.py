"""Tests for MeasureIt options flow in config_flow class."""

from unittest.mock import patch

import pytest
from homeassistant import data_entry_flow
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_DEVICE_CLASS, CONF_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.measureit.const import (
    CONF_CONDITION,
    CONF_CONFIG_NAME,
    CONF_COUNTER_TEMPLATE,
    CONF_INDEX,
    CONF_METER_TYPE,
    CONF_SENSOR_NAME,
    CONF_TW_DAYS,
    CONF_TW_FROM,
    CONF_TW_TILL,
    DOMAIN,
)


@pytest.fixture(name="loaded_counter_entry")
async def load_counter_integration(hass: HomeAssistant) -> MockConfigEntry:
    """Set up a counter config entry in Home Assistant."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        options={
            CONF_CONFIG_NAME: "counter_config",
            CONF_METER_TYPE: "counter",
            CONF_COUNTER_TEMPLATE: "{{ is_state('binary_sensor.test_sensor', 'on') }}",
            CONF_CONDITION: "{{ True }}",
            CONF_TW_DAYS: ["0", "1", "2", "3", "4", "5", "6"],
            CONF_TW_FROM: "00:00:00",
            CONF_TW_TILL: "00:00:00",
            "sensor": [
                {
                    "state_class": "total_increasing",
                    "unique_id": "ca100892-b6bb-11ee-923e-0242ac110003",
                    "sensor_name": "day",
                    "cron": "0 0 * * *",
                    "period": "day",
                },
            ],
        },
        entry_id="2",
    )

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    return config_entry


async def start_edit_main_flow(
    hass: HomeAssistant, entry: MockConfigEntry
) -> data_entry_flow.FlowResult:
    """Open the options flow and select editing the main config."""
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "edit_main"}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "edit_main"
    return result


def get_suggested_value(result: data_entry_flow.FlowResult, key: str) -> str | None:
    """Return the value suggested for a key in the form shown to the user."""
    for schema_key in result["data_schema"].schema:
        if schema_key == key:
            return schema_key.description.get("suggested_value")
    return None


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


async def test_edit_sensor_uom(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Test the config flow for setting up a config with counter meters."""
    result = await hass.config_entries.options.async_init(loaded_entry.entry_id)

    # Check that the options flow shows the form with actions
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

    # Choose the action
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_edit_sensor"}
    )

    # Check that the config flow shows the form for choosing a sensor to edit
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "select_edit_sensor"

    # Choose the sensor to edit
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_INDEX: "0"}
    )

    # Check that the config flow shows the form with sensor config
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "edit_sensor"

    # Fill config name
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SENSOR_NAME: "day", CONF_UNIT_OF_MEASUREMENT: "h"},
    )

    assert result["errors"] is None
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "thank_you"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY

    config_entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert config_entry.data == {}
    assert config_entry.options.get(CONF_CONFIG_NAME) == "time_config"
    assert config_entry.options["sensor"][0].get(CONF_UNIT_OF_MEASUREMENT) == "h"


async def test_edit_sensor_uom_with_device_class(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Test the config flow for setting up a config with counter meters."""
    result = await hass.config_entries.options.async_init(loaded_entry.entry_id)

    # Check that the options flow shows the form with actions
    assert result["type"] == data_entry_flow.FlowResultType.MENU
    assert result["step_id"] == "init"

    # Choose the action
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_edit_sensor"}
    )

    # Check that the config flow shows the form for choosing a sensor to edit
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "select_edit_sensor"

    # Choose the sensor to edit
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_INDEX: "0"}
    )

    # Check that the config flow shows the form with sensor config
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "edit_sensor"

    # Fill config name
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SENSOR_NAME: "day",
            CONF_UNIT_OF_MEASUREMENT: "h",
            CONF_DEVICE_CLASS: "duration",
        },
    )

    assert result["errors"] == {"base": "uom_with_device_class_update"}
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "edit_sensor"


async def test_edit_counter_template(
    hass: HomeAssistant, loaded_counter_entry: MockConfigEntry
) -> None:
    """Test that the counter template can be viewed and edited (issue #221)."""
    result = await start_edit_main_flow(hass, loaded_counter_entry)

    # The current template should be shown so it can be changed instead of retyped
    assert (
        get_suggested_value(result, CONF_COUNTER_TEMPLATE)
        == "{{ is_state('binary_sensor.test_sensor', 'on') }}"
    )

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_COUNTER_TEMPLATE: "{{ is_state('binary_sensor.other', 'on') }}",
            CONF_TW_DAYS: ["0", "1"],
            CONF_TW_FROM: "00:00:00",
            CONF_TW_TILL: "00:00:00",
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY

    assert (
        loaded_counter_entry.options[CONF_COUNTER_TEMPLATE]
        == "{{ is_state('binary_sensor.other', 'on') }}"
    )
    assert loaded_counter_entry.options[CONF_TW_DAYS] == ["0", "1"]


async def test_edit_main_config_with_invalid_condition(
    hass: HomeAssistant, loaded_counter_entry: MockConfigEntry
) -> None:
    """Test that a condition which cannot be rendered is rejected."""
    result = await start_edit_main_flow(hass, loaded_counter_entry)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_COUNTER_TEMPLATE: "{{ is_state('binary_sensor.other', 'on') }}",
            CONF_CONDITION: "{{ 1 / 0 }}",
            CONF_TW_DAYS: ["0", "1"],
            CONF_TW_FROM: "00:00:00",
            CONF_TW_TILL: "00:00:00",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "edit_main"
    assert result["errors"] == {"base": "condition_invalid"}

    # The config entry should be untouched
    assert (
        loaded_counter_entry.options[CONF_COUNTER_TEMPLATE]
        == "{{ is_state('binary_sensor.test_sensor', 'on') }}"
    )


async def test_edit_main_config_without_days(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """Test that the time window is validated when editing the main config."""
    result = await start_edit_main_flow(hass, loaded_entry)

    # A time meter has no counter template to edit
    assert CONF_COUNTER_TEMPLATE not in result["data_schema"].schema

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_TW_DAYS: [],
            CONF_TW_FROM: "00:00:00",
            CONF_TW_TILL: "00:00:00",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "edit_main"
    assert result["errors"] == {"base": "tw_days_minimum"}
