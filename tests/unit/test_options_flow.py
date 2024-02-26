"""Tests for MeasureIt options flow in config_flow class."""

from unittest.mock import patch

import pytest
from homeassistant import data_entry_flow
from homeassistant.const import CONF_DEVICE_CLASS, CONF_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.measureit.const import (CONF_CONFIG_NAME, CONF_INDEX,
                                               CONF_SENSOR_NAME, DOMAIN)


# This fixture bypasses the actual setup of the integration
# since we only want to test the config flow. We test the
# actual functionality of the integration in other test modules.
@pytest.fixture(autouse=True)
def bypass_setup_fixture():
    """Prevent setup."""
    with patch(
        "custom_components.measureit.async_setup",
        return_value=True,
    ), patch(
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
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "select_edit_sensor"

    # Choose the sensor to edit
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_INDEX: "0"}
    )

    # Check that the config flow shows the form with sensor config
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "edit_sensor"

    # Fill config name
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SENSOR_NAME: "day", CONF_UNIT_OF_MEASUREMENT: "h"},
    )

    assert result["errors"] is None
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
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
    assert result["type"] == data_entry_flow.RESULT_TYPE_MENU
    assert result["step_id"] == "init"

    # Choose the action
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "select_edit_sensor"}
    )

    # Check that the config flow shows the form for choosing a sensor to edit
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "select_edit_sensor"

    # Choose the sensor to edit
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_INDEX: "0"}
    )

    # Check that the config flow shows the form with sensor config
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "edit_sensor"

    # Fill config name
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SENSOR_NAME: "day", CONF_UNIT_OF_MEASUREMENT: "h", CONF_DEVICE_CLASS: "duration"},
    )

    assert result["errors"] == {'base': 'uom_with_device_class_update'}
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "edit_sensor"
