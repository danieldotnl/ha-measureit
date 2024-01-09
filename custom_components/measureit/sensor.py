"""Sensor platform for MeasureIt."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_UNIT_OF_MEASUREMENT
from homeassistant.const import CONF_VALUE_TEMPLATE, CONF_UNIQUE_ID
from homeassistant.core import callback
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity, ExtraStoredData
from homeassistant.util import dt as dt_util


from .period import Period
from .reading import ReadingData

from .const import (
    ATTR_NEXT_RESET,
    CONF_CONFIG_NAME,
    CONF_CRON,
    CONF_SENSOR,
    CONF_SENSOR_NAME,
    SOURCE_ENTITY_ID,
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
    source_entity_id = hass.data[DOMAIN_DATA][entry_id].get(SOURCE_ENTITY_ID)

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
                source_entity_id,
            )
        )

    async_add_entities(sensors)


@dataclass
class MeasureItMeterStoredData(ExtraStoredData):
    """Object to hold meter data to be stored."""

    state: str | None = None
    measured_value: float = 0
    prev_measured_value: float = 0
    session_start_reading: float | None = None
    start_measured_value: float | None = None
    period_last_reset: datetime | None = None
    period_end: datetime | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a dict representation of the meter data."""

        _LOGGER.debug("Persisting meter data")

        data = {
            "measured_value": self.measured_value,
            "start_measured_value": self.start_measured_value,
            "prev_measured_value": self.prev_measured_value,
            "session_start_reading": self.session_start_reading,
            "period_last_reset": dt_util.as_timestamp(self.period_last_reset),
            "period_end": dt_util.as_timestamp(self.period_end),
            "state": self.state,
        }
        return data

    @classmethod
    def from_dict(cls, restored: dict[str, Any]) -> MeasureItMeterStoredData | None:
        """Initialize a stored sensor state from a dict."""

        try:
            measured_value = restored["measured_value"]
            start_measured_value = restored["start_measured_value"]
            prev_measured_value = restored["prev_measured_value"]
            session_start_reading = restored["session_start_reading"]
            period_last_reset = dt_util.utc_from_timestamp(
                restored["period_last_reset"]
            )
            period_end = dt_util.utc_from_timestamp(restored["period_end"])
            state = restored["state"]
        except KeyError:
            # restored is a dict, but does not have all values
            return None

        return cls(
            state,
            measured_value,
            prev_measured_value,
            session_start_reading,
            start_measured_value,
            period_last_reset,
            period_end,
        )


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
        source_entity_id=None,
    ):
        """Initialize a sensor entity."""
        self._meter_type = meter_type
        self.meter: Meter = meter
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
        self._source_entity_id = source_entity_id

        if self._meter_type == METER_TYPE_TIME:
            self._attr_device_class = SensorDeviceClass.DURATION

    async def async_added_to_hass(self):
        """Add sensors as a listener for coordinator updates."""

        if (last_meter_data := await self.async_get_last_sensor_data()) is not None:
            _LOGGER.debug(
                "%s # Restoring data from last session: %s",
                self._attr_name,
                last_meter_data,
            )
            self.meter.state = last_meter_data.state
            self.meter.measured_value = last_meter_data.measured_value
            self.meter._start_measured_value = last_meter_data.start_measured_value
            self.meter.prev_measured_value = last_meter_data.prev_measured_value
            self.meter._session_start_reading = last_meter_data.session_start_reading
            self.meter._period.last_reset = last_meter_data.period_last_reset
            self.meter._period.end = last_meter_data.period_end
        else:
            _LOGGER.warning("%s # Could not restore data", self._attr_name)

        self.async_on_remove(
            self._coordinator.async_add_listener(self._handle_coordinator_update)
        )

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the state attributes."""
        attributes = {
            ATTR_STATUS: self.meter.state,
            ATTR_PREV: self._value_template_renderer(self.meter.prev_measured_value),
            ATTR_NEXT_RESET: self.meter.next_reset,
        }
        if self._source_entity_id:
            attributes.update({SOURCE_ENTITY_ID: self._source_entity_id})
        return attributes

    @callback
    def _handle_coordinator_update(self, reading: ReadingData) -> None:
        """Handle updated data from the coordinator."""

        _LOGGER.debug("Coordinator update received!")

        self.meter.on_update(reading)
        self._attr_native_value = self._value_template_renderer(
            self.meter.measured_value
        )
        self.async_write_ha_state()

    @property
    def extra_restore_state_data(self) -> MeasureItMeterStoredData:
        """Return sensor specific state data to be restored."""

        return MeasureItMeterStoredData(
            self.meter.state,
            self.meter.measured_value,
            self.meter.prev_measured_value,
            self.meter._session_start_reading,
            self.meter._start_measured_value,
            self.meter._period.last_reset,
            self.meter._period.end,
        )

    async def async_get_last_sensor_data(self) -> MeasureItMeterStoredData | None:
        """Restore native_value and native_unit_of_measurement."""
        if (restored_last_extra_data := await self.async_get_last_extra_data()) is None:
            return None
        return MeasureItMeterStoredData.from_dict(restored_last_extra_data.as_dict())
