"""Sensor platform for MeasureIt."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_UNIT_OF_MEASUREMENT
from homeassistant.const import CONF_VALUE_TEMPLATE, CONF_UNIQUE_ID
from homeassistant.core import callback
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .period import Period
from .reading import ReadingData

from .const import (
    ATTR_NEXT_RESET,
    CONF_CONFIG_NAME,
    CONF_CRON,
    CONF_SENSOR,
    CONF_SENSOR_NAME,
)
from .const import ATTR_PREV
from .const import ATTR_STATUS
from .const import CONF_METER_TYPE
from .const import COORDINATOR
from .const import DOMAIN_DATA
from .const import ICON
from .const import METER_TYPE_TIME
from .coordinator import MeasureItCoordinator
from .meter import Meter
from .util import create_renderer


_LOGGER: logging.Logger = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor platform."""
    entry_id: str = config_entry.entry_id
    meter_type: str = config_entry.options[CONF_METER_TYPE]
    _LOGGER.debug("Options: %s", config_entry.options)
    config_name: str = config_entry.options[CONF_CONFIG_NAME]

    coordinator = hass.data[DOMAIN_DATA][entry_id][COORDINATOR]

    sensors: list[MeasureItSensor] = []

    for sensor in config_entry.options[CONF_SENSOR]:
        value_template_renderer = None
        unique_id = sensor.get(CONF_UNIQUE_ID)

        period = Period(sensor[CONF_CRON], dt_util.now())
        meter = Meter(f"{config_name}_{sensor[CONF_SENSOR_NAME]}", period)

        value_template_renderer = create_renderer(hass, sensor.get(CONF_VALUE_TEMPLATE))

        sensors.append(
            MeasureItSensor(
                coordinator,
                meter,
                unique_id,
                config_name,
                meter_type,
                sensor[CONF_SENSOR_NAME],
                value_template_renderer,
                sensor.get(CONF_UNIT_OF_MEASUREMENT),
            )
        )

    async_add_entities(sensors)


class MeasureItSensor(RestoreEntity, SensorEntity):
    """MeasureIt Sensor Entity."""

    def __init__(
        self,
        coordinator,
        meter,
        unique_id,
        config_name,
        meter_type,
        pattern_name,
        value_template_renderer,
        unit_of_measurement,
    ):
        """Initialize a sensor entity."""
        self._meter_type = meter_type
        self.meter = meter
        self._coordinator: MeasureItCoordinator = coordinator
        self._pattern_name = pattern_name
        self._attr_name = f"{config_name}_{pattern_name}"
        self._attr_unique_id = unique_id
        self._attr_icon = ICON
        self._attr_extra_state_attributes = {}
        self._value_template_renderer = value_template_renderer
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_should_poll = False

        if self._meter_type == METER_TYPE_TIME:
            self._attr_device_class = SensorDeviceClass.DURATION

    async def async_added_to_hass(self):
        """Add sensors as a listener for coordinator updates."""
        self.async_on_remove(
            self._coordinator.async_add_listener(self._handle_coordinator_update)
        )

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the state attributes."""
        return {
            ATTR_STATUS: self.meter.state,
            ATTR_PREV: self._value_template_renderer(self.meter.prev_measured_value),
            ATTR_NEXT_RESET: self.meter.next_reset,
        }

    @callback
    def _handle_coordinator_update(self, reading: ReadingData) -> None:
        """Handle updated data from the coordinator."""

        self.meter.on_update(reading)
        self._attr_native_value = self._value_template_renderer(
            self.meter.measured_value
        )
        self.async_write_ha_state()
