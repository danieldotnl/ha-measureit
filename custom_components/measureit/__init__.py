"""MeasureIt integration."""

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.template import Template

from .const import (CONF_CONDITION, CONF_CONFIG_NAME, CONF_COUNTER_TEMPLATE,
                    CONF_METER_TYPE, CONF_SOURCE, CONF_TW_DAYS, CONF_TW_FROM,
                    CONF_TW_TILL, COORDINATOR, DOMAIN_DATA, MeterType)
from .coordinator import MeasureItCoordinator
from .time_window import TimeWindow

_LOGGER: logging.Logger = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""

    _LOGGER.debug("Config entry:\n%s", entry.options)

    config_name: str = entry.options[CONF_CONFIG_NAME]
    meter_type: str = entry.options[CONF_METER_TYPE]

    if condition_template := entry.options.get(CONF_CONDITION):
        condition_template = Template(condition_template, hass)
        condition_template.ensure_valid()

    if counter_template := entry.options.get(CONF_COUNTER_TEMPLATE):
        counter_template = Template(counter_template, hass)
        counter_template.ensure_valid()

    source_entity = None

    if meter_type == MeterType.SOURCE:
        registry = er.async_get(hass)

        try:
            source_entity = er.async_validate_entity_id(
                registry, entry.options[CONF_SOURCE]
            )
        except vol.Invalid:
            # The entity is identified by an unknown entity registry ID
            _LOGGER.error(
                "%s # Failed to setup MeasureIt due to unknown source entity %s",
                config_name,
                entry.options[CONF_SOURCE],
            )
            return False

    time_window = TimeWindow(
        entry.options[CONF_TW_DAYS],
        entry.options[CONF_TW_FROM],
        entry.options[CONF_TW_TILL],
    )

    coordinator = MeasureItCoordinator(
        hass,
        config_name,
        meter_type,
        time_window,
        condition_template,
        counter_template,
        source_entity,
    )
    hass.data.setdefault(DOMAIN_DATA, {}).setdefault(entry.entry_id, {}).update(
        {
            COORDINATOR: coordinator,
        }
    )

    await hass.config_entries.async_forward_entry_setups(entry, ([Platform.SENSOR]))

    @callback
    def run_start(event):
        # pylint: disable=unused-argument
        _LOGGER.debug("%s # Start coordinator", config_name)
        coordinator.start()

    if hass.state != CoreState.running:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, run_start)
    else:
        run_start(None)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = hass.data[DOMAIN_DATA][entry.entry_id][COORDINATOR]
    coordinator.stop()

    if unload_ok := await hass.config_entries.async_unload_platforms(
        entry,
        (Platform.SENSOR,),
    ):
        hass.data[DOMAIN_DATA].pop(entry.entry_id)

    return unload_ok
