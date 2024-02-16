"""Tests for MeasureIt config_flow class."""

from unittest.mock import patch
from homeassistant.core import HomeAssistant
from homeassistant import config_entries, data_entry_flow
from homeassistant.data_entry_flow import FlowResultType
import pytest

from homeassistant.const import CONF_UNIT_OF_MEASUREMENT, CONF_DEVICE_CLASS

from custom_components.measureit.const import (
    CONF_CONDITION,
    CONF_CONFIG_NAME,
    CONF_PERIODS,
    CONF_TW_DAYS,
    CONF_TW_FROM,
    CONF_TW_TILL,
    CONF_STATE_CLASS,
    DOMAIN,
)


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
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM

    # Fill config name
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_CONFIG_NAME: "test_config_time"}
    )

    assert result["errors"] is None
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
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
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "sensors"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_PERIODS: ["day", "week", "forever"],
            CONF_UNIT_OF_MEASUREMENT: "s",
            CONF_DEVICE_CLASS: "duration",
            CONF_STATE_CLASS: "total_increasing",
        },
    )

    assert result["errors"] is None
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "thank_you"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY


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
