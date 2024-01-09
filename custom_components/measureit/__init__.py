"""MeasureIt integration."""
import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import Config, CoreState, callback
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.template import Template
from homeassistant.util import dt as dt_util

from .const import CONF_CONDITION, CONF_CONFIG_NAME, SOURCE_ENTITY_ID
from .const import CONF_METER_TYPE
from .const import CONF_SOURCE
from .const import CONF_TW_DAYS
from .const import CONF_TW_FROM
from .const import CONF_TW_TILL
from .const import COORDINATOR
from .const import DOMAIN_DATA
from .const import METER_TYPE_SOURCE
from .const import METER_TYPE_TIME
from .coordinator import MeasureItCoordinator
from .time_window import TimeWindow

STORAGE_VERSION = 1
STORAGE_KEY_TEMPLATE = "{domain}_{entry_id}"

_LOGGER: logging.Logger = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: Config):
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""

    config_name: str = entry.options[CONF_CONFIG_NAME]
    meter_type: str = entry.options[CONF_METER_TYPE]
    condition: str | None = entry.options.get(CONF_CONDITION)

    def get_time_value():
        return dt_util.utcnow().timestamp()

    def get_source_value():
        _LOGGER.debug("Reading state from source entity: %s", source_entity)
        return hass.states.get(source_entity).state

    if meter_type == METER_TYPE_TIME:
        value_callback = get_time_value
    elif meter_type == METER_TYPE_SOURCE:
        registry = er.async_get(hass)

        try:
            source_entity = er.async_validate_entity_id(
                registry, entry.options[CONF_SOURCE]
            )
            hass.data.setdefault(DOMAIN_DATA, {}).setdefault(entry.entry_id, {}).update(
                {
                    SOURCE_ENTITY_ID: entry.options[CONF_SOURCE],
                }
            )
        except vol.Invalid:
            # The entity is identified by an unknown entity registry ID
            _LOGGER.error(
                "%s # Failed to setup MeasureIt for unknown entity %s",
                config_name,
                entry.options[CONF_SOURCE],
            )
            return False

        value_callback = get_source_value

    if condition:
        condition = Template(condition)
        condition.ensure_valid()

    time_window = TimeWindow(
        entry.options[CONF_TW_DAYS],
        entry.options[CONF_TW_FROM],
        entry.options[CONF_TW_TILL],
    )

    coordinator = MeasureItCoordinator(
        hass, config_name, condition, time_window, value_callback
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
