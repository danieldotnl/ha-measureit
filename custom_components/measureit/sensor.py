"""Sensor platform for MeasureIt."""
import logging
from decimal import Decimal
from datetime import datetime
from typing import Any
from dataclasses import dataclass
from croniter import croniter

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import SensorStateClass, DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_UNIT_OF_MEASUREMENT
from homeassistant.const import CONF_VALUE_TEMPLATE, CONF_UNIQUE_ID
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity, ExtraStoredData
from homeassistant.util import dt as dt_util

from .period import Period
from .const import (
    ATTR_NEXT_RESET,
    CONF_CONFIG_NAME,
    CONF_CRON,
    CONF_SENSOR,
    CONF_SENSOR_NAME,
    DOMAIN,
    SOURCE_ENTITY_ID,
    SensorState,
)
from .const import ATTR_PREV
from .const import ATTR_STATUS
from .const import CONF_METER_TYPE
from .const import COORDINATOR
from .const import DOMAIN_DATA
from .const import ICON
from .coordinator import MeasureItCoordinator
from .meter import MeasureItMeter
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
        sensor_name = f"{config_name}_{sensor[CONF_SENSOR_NAME]}"

        Period(sensor[CONF_CRON], dt_util.now())
        # meter = TimeM(f"{config_name}_{sensor[CONF_SENSOR_NAME]}", period)

        value_template_renderer = create_renderer(hass, sensor.get(CONF_VALUE_TEMPLATE))

        sensor_entity = MeasureItSensor(
            coordinator,
            meter,
            unique_id,
            meter_type,
            sensor_name,
            value_template_renderer,
            sensor.get(CONF_UNIT_OF_MEASUREMENT),
            source_entity_id,
        )
        sensors.append(sensor_entity)
        hass.data[DOMAIN][SENSOR_DOMAIN].update(
            {f"{SENSOR_DOMAIN}.{sensor_name}": sensor_entity}
        )

    async_add_entities(sensors)


def temp_parse_timestamp_or_string(timestamp_or_string: str) -> datetime | None:
    """Parse a timestamp or string into a datetime object."""

    try:
        return datetime.fromisoformat(timestamp_or_string).replace(
            tzinfo=dt_util.DEFAULT_TIME_ZONE
        )
    except (TypeError, ValueError):
        try:
            return datetime.fromtimestamp(
                float(timestamp_or_string), dt_util.DEFAULT_TIME_ZONE
            )
        except OverflowError:
            return None


@dataclass
class MeasureItSensorStoredData(ExtraStoredData):
    """Object to hold meter data to be stored."""

    sensor_state: str | None = None
    last_reset: datetime | None = None
    meter_data: dict = {}
    time_window_active: bool = None
    condition_active: bool = None
    next_reset: datetime | None = None

    # measured_value: float = 0
    # prev_measured_value: float = 0
    # session_start_reading: float | None = None
    # start_measured_value: float | None = None
    # period_last_reset: datetime | None = None
    # period_end: datetime | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a dict representation of the meter data."""

        _LOGGER.debug("Persisting meter data")

        data = {
            "measured_value": self.measured_value,
            "start_measured_value": self.start_measured_value,
            "prev_measured_value": self.prev_measured_value,
            "session_start_reading": self.session_start_reading,
            "period_last_reset": self.period_last_reset.isoformat(),
            "period_end": self.period_end.isoformat(),
            "state": self.state,
        }
        return data

    @classmethod
    def from_dict(cls, restored: dict[str, Any]):  # -> MeasureItSensorStoredData:
        """Initialize a stored sensor state from a dict."""

        try:
            measured_value = restored["measured_value"]
            start_measured_value = restored["start_measured_value"]
            prev_measured_value = restored["prev_measured_value"]
            session_start_reading = restored["session_start_reading"]
            period_last_reset = temp_parse_timestamp_or_string(
                restored["period_last_reset"]
            )
            period_end = temp_parse_timestamp_or_string(restored["period_end"])
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
        hass: HomeAssistant,
        coordinator: MeasureItCoordinator,
        meter: MeasureItMeter,
        unique_id: str,
        sensor_name: str,
        reset_pattern: str,
        value_template_renderer,
        unit_of_measurement: str | None = None,
        state_class: SensorStateClass | None = None,
        device_class: SensorDeviceClass | None = None,
    ):
        """Initialize a sensor entity."""
        self.hass = hass
        self._coordinator = coordinator
        self.meter = meter
        self._attr_unique_id = unique_id
        self._attr_name = sensor_name
        self._reset_pattern = reset_pattern
        self._value_template_renderer = value_template_renderer
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_state_class = state_class
        self._attr_device_class = device_class

        self._attr_icon = ICON
        self._attr_should_poll = False

        self._time_window_active: bool = False
        self._condition_active: bool = False
        self._reset_listener = None
        self._next_reset: datetime | None = None

    async def async_added_to_hass(self):
        """Add sensors as a listener for coordinator updates."""

        if (last_sensor_data := await self.async_get_last_sensor_data()) is not None:
            _LOGGER.debug(
                "%s # Restoring data from last session: %s",
                self._attr_name,
                last_sensor_data,
            )
            self.meter.state = last_sensor_data.state
            self.meter.measured_value = last_sensor_data.measured_value
            self.meter._start_measured_value = last_sensor_data.start_measured_value
            self.meter.prev_measured_value = last_sensor_data.prev_measured_value
            self.meter._session_start_reading = last_sensor_data.session_start_reading
            self.meter._period.last_reset = last_sensor_data.period_last_reset
            self.meter._period.end = last_sensor_data.period_end

            self.schedule_next_reset(last_sensor_data.next_reset)
        else:
            _LOGGER.warning("%s # Could not restore data", self._attr_name)
            self.schedule_next_reset()

        self.async_on_remove(self._coordinator.register(self))

    @callback
    def unsub_reset_listener(self):
        """Unsubscribe and remove the reset listener."""
        if self._reset_listener:
            self._reset_listener()
            self._reset_listener = None

    @property
    def sensor_state(self) -> SensorState:
        """Return the sensor state."""
        if self._condition_active is True and self._time_window_active is True:
            return SensorState.MEASURING
        elif self._time_window_active is False:
            return SensorState.WAITING_FOR_TIME_WINDOW
        elif self._condition_active is False:
            return SensorState.WAITING_FOR_CONDITION
        else:
            raise ValueError("Invalid sensor state determined.")

    @property
    def native_value(self) -> Decimal | None:
        """Return the state of the sensor."""
        return self._value_template_renderer(self.meter.measured_value)

    @property
    def prev_native_value(self) -> Decimal | None:
        """Return the state of the sensor."""
        return self._value_template_renderer(self.meter.prev_measured_value)

    @property
    def next_reset(self) -> datetime | None:
        """Return the next reset."""
        return self._next_reset

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the state attributes."""
        attributes = {
            ATTR_STATUS: self.sensor_state,
            ATTR_PREV: self._value_template_renderer(self.meter.prev_measured_value),
            ATTR_NEXT_RESET: self._next_reset,
        }
        return attributes

    @callback
    def reset(self):
        """Reset the sensor."""
        reset_datetime = dt_util.now()
        _LOGGER.info("Resetting sensor %s at %s", self._attr_name, reset_datetime)
        self.meter.reset()
        self._attr_last_reset = reset_datetime

        self.schedule_next_reset()
        self._async_write_ha_state()

    @callback
    def schedule_next_reset(self, next_reset: datetime | None = None):
        """Set the next reset moment."""
        tznow = dt_util.now()
        if next_reset and next_reset <= tznow:
            self.reset()
        elif not next_reset:
            if self._reset_pattern:
                next_reset = croniter(self._reset_pattern, tznow).get_next(datetime)
            else:
                self._next_reset = None
                return

        self._next_reset = next_reset
        if self._reset_listener:
            self._reset_listener()
        self._reset_listener = async_track_point_in_time(
            self.hass,
            self.reset,
            self._next_reset,
        )

    @callback
    def on_condition_template_change(self, condition_active: bool) -> None:
        """Handle a change in the condition template."""
        old_state = self.sensor_state
        self._condition_active = condition_active
        new_state = self.sensor_state
        self._on_sensor_state_update(old_state, new_state)
        self._async_write_ha_state()

    @callback
    def on_time_window_change(self, time_window_active: bool) -> None:
        """Handle a change in the time window."""
        old_state = self.sensor_state
        self._time_window_active = time_window_active
        new_state = self.sensor_state
        self._on_sensor_state_update(old_state, new_state)
        self._async_write_ha_state()

    @callback
    def on_value_change(self, new_value: float) -> None:
        """Handle a change in the value."""
        self.meter.update(new_value)
        self._async_write_ha_state()

    def _on_sensor_state_update(
        self, old_state: SensorState, new_state: SensorState
    ) -> None:
        """Start/stop meter when needed."""
        if new_state == old_state:
            return
        if new_state == SensorState.MEASURING:
            self.meter.start()
        if old_state == SensorState.MEASURING:
            self.meter.stop()

    @property
    def extra_restore_state_data(self) -> MeasureItSensorStoredData:
        """Return sensor specific state data to be stored."""

        return MeasureItSensorStoredData(
            self.meter.state,
            self.meter.measured_value,
            self.meter.prev_measured_value,
            self.meter._session_start_reading,
            self.meter._start_measured_value,
            self.meter._period.last_reset,
            self.meter._period.end,
        )

    async def async_get_last_sensor_data(self) -> MeasureItSensorStoredData | None:
        """Retrieve sensor data to be restored."""
        if (restored_last_extra_data := await self.async_get_last_extra_data()) is None:
            return None
        return MeasureItSensorStoredData.from_dict(restored_last_extra_data.as_dict())
