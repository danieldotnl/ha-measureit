"""Tests for MeasureIt integration."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def setup_with_mock_config(hass: HomeAssistant, entry: MockConfigEntry):
    """Set up the MeasureIt integration with a mock config entry."""
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
