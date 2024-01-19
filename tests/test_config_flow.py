"""Tests for MeasureIt config_flow class."""
from unittest.mock import patch
from homeassistant.core import HomeAssistant
from homeassistant import config_entries, data_entry_flow
from homeassistant.data_entry_flow import FlowResultType
import pytest

from custom_components.measureit.const import CONF_CONFIG_NAME, DOMAIN


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


async def test_config_flow(hass: HomeAssistant) -> None:
    """Test the configuration flow for setting up a MeasureIt."""
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

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM

    # Fill form name
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_CONFIG_NAME: "test_configname_time"}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
