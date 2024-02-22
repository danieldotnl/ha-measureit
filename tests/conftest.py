"""Global fixtures for Vaillant vSMART integration."""

# Fixtures allow you to replace functions with a Mock object. You can perform
# many options via the Mock to reflect a particular behavior from the original
# function that you want to see without going through the function's actual logic.
# Fixtures can either be passed into tests as parameters, or if autouse=True, they
# will automatically be used across all tests.
#
# Fixtures that are defined in conftest.py are available across all tests. You can also
# define fixtures within a particular test file to scope them locally.
#
# pytest_homeassistant_custom_component provides some fixtures that are provided by
# Home Assistant core. You can find those fixture definitions here:
# https://github.com/MatthewFlamm/pytest-homeassistant-custom-component/blob/master/pytest_homeassistant_custom_component/common.py
#
# See here for more info: https://docs.pytest.org/en/latest/fixture.html (note that
# pytest includes fixtures OOB which you can use as defined on this page)
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.measureit.const import (CONF_CONFIG_NAME,
                                               CONF_METER_TYPE, DOMAIN)

pytest_plugins = "pytest_homeassistant_custom_component"


# This fixture enables loading custom integrations in all tests.
# Remove to enable selective use of this fixture
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """TODO."""
    yield


# This fixture is used to prevent HomeAssistant from attempting to create and dismiss persistent
# notifications. These calls would fail without this fixture since the persistent_notification
# integration is never loaded during a test.
@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with patch("homeassistant.components.persistent_notification.async_create"), patch(
        "homeassistant.components.persistent_notification.async_dismiss"
    ):
        yield


@pytest.fixture(name="get_time_config")
async def get_time_config_to_integration_load() -> dict[str, Any]:
    """Return default minimal time configuration.

    To override the config, tests can be marked with:
    @pytest.mark.parametrize("get_time_config", [{...}])
    """
    return {
        CONF_CONFIG_NAME: "time_config",
        CONF_METER_TYPE: "time",
        "sensor": [
            {
                "unit_of_measurement": "s",
                "state_class": "total",
                "device_class": "duration",
                "unique_id": "ca100892-b6bb-11ee-923e-0242ac110002",
                "sensor_name": "day",
                "cron": "0 0 * * *",
                "period": "day",
            },
        ],
    }


@pytest.fixture(name="loaded_entry")
async def load_integration(
    hass: HomeAssistant, get_time_config: dict[str, Any]
) -> MockConfigEntry:
    """Set up the Scrape integration in Home Assistant."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        options=get_time_config,
        entry_id="1",
    )

    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    return config_entry
