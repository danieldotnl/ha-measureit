"""Sensor platform for MeasureIt."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from cronsim import CronSim
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_DEVICE_CLASS,
    CONF_UNIQUE_ID,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_VALUE_TEMPLATE,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform
from homeassistant.helpers.config_validation import make_entity_service_schema
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.restore_state import ExtraStoredData, RestoreEntity
from homeassistant.helpers.template import is_number
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_LAST_RESET,
    ATTR_NEXT_RESET,
    ATTR_PREV,
    ATTR_STATUS,
    CONF_CONFIG_NAME,
    CONF_CRON,
    CONF_METER_TYPE,
    CONF_SENSOR,
    CONF_SENSOR_NAME,
    CONF_STATE_CLASS,
    COORDINATOR,
    DOMAIN_DATA,
    MeterType,
    SensorState,
)
from .coordinator import MeasureItCoordinator, MeasureItCoordinatorEntity
from .meter import CounterMeter, MeasureItMeter, SourceMeter, TimeMeter
from .util import create_renderer

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER: logging.Logger = logging.getLogger(__name__)


def validate_is_number(value: Any) -> bool:
    """Validate value is a number."""
    if is_number(value):
        return value
    msg = "Value is not a number"
    raise vol.Invalid(msg)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor platform."""
    entry_id: str = config_entry.entry_id
    meter_type: MeterType = config_entry.options[CONF_METER_TYPE]
    config_name: str = config_entry.options[CONF_CONFIG_NAME]

    coordinator = hass.data[DOMAIN_DATA][entry_id][COORDINATOR]

    sensors: list[MeasureItSensor] = []
    for sensor in config_entry.options[CONF_SENSOR]:
        unique_id = sensor.get(CONF_UNIQUE_ID)
        sensor_name = f"{config_name}_{sensor[CONF_SENSOR_NAME]}"
        reset_pattern = sensor.get(CONF_CRON)
        state_class = sensor.get(CONF_STATE_CLASS)
        device_class = sensor.get(CONF_DEVICE_CLASS)
        uom = sensor.get(CONF_UNIT_OF_MEASUREMENT)

        if meter_type == MeterType.SOURCE:
            meter = SourceMeter()
            value_template_renderer = create_renderer(
                hass, sensor.get(CONF_VALUE_TEMPLATE), 3
            )
        elif meter_type == MeterType.COUNTER:
            meter = CounterMeter()
            value_template_renderer = create_renderer(
                hass, sensor.get(CONF_VALUE_TEMPLATE)
            )
        elif meter_type == MeterType.TIME:
            meter = TimeMeter()
            value_template_renderer = create_renderer(
                hass, sensor.get(CONF_VALUE_TEMPLATE), 0
            )
        else:
            _LOGGER.error("%s # Invalid meter type: %s", config_name, meter_type)
            msg = f"Invalid meter type: {meter_type}"
            raise ValueError(msg)

        sensor_entity = MeasureItSensor(
            hass,
            coordinator,
            meter,
            unique_id,
            sensor_name,
            reset_pattern,
            value_template_renderer,
            state_class,
            device_class,
            uom,
        )
        sensors.append(sensor_entity)

    async_add_entities(sensors)

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        "calibrate",
        make_entity_service_schema(
            {
                vol.Required(ATTR_ENTITY_ID): vol.All(cv.ensure_list, [cv.entity_id]),
                vol.Required("value"): validate_is_number,
            }
        ),
        "calibrate",
    )

    platform.async_register_entity_service(
        "reset",
        make_entity_service_schema(
            {
                vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
                vol.Optional("reset_datetime"): cv.datetime,
            }
        ),
        "on_reset_service_triggered",
    )


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

    meter_data: dict
    time_window_active: bool
    active: bool
    last_reset: datetime | None
    next_reset: datetime | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a dict representation of the meter data."""
        _LOGGER.debug("Persisting meter data")

        return {
            "meter_data": self.meter_data,
            "time_window_active": self.time_window_active,
            "active": self.active,
            "last_reset": self.last_reset.isoformat() if self.last_reset else None,
            "next_reset": self.next_reset.isoformat() if self.next_reset else None,
        }

    @classmethod
    def from_old_format_dict(
        cls, restored: dict[str, Any]
    ) -> MeasureItSensorStoredData:
        """Initialize a stored sensor state from an old format dict."""
        time_window_active = False
        active = False
        if restored.get("state") == SensorState.MEASURING:
            time_window_active = True
            active = True
        elif restored.get("state") == SensorState.WAITING_FOR_TIME_WINDOW:
            time_window_active = False
            active = True
        elif restored.get("state") == SensorState.WAITING_FOR_CONDITION:
            time_window_active = True
            active = False
        meter_data = {
            "measured_value": restored["measured_value"],
            "session_start_value": restored["session_start_reading"],
            "session_start_measured_value": restored["start_measured_value"],
            "prev_measured_value": restored["prev_measured_value"],
            "measuring": restored["state"] == SensorState.MEASURING,
        }
        if meter_data["session_start_value"] is None:
            meter_data["session_start_value"] = 0
        if meter_data["session_start_measured_value"] is None:
            meter_data["session_start_measured_value"] = 0

        last_reset = temp_parse_timestamp_or_string(restored["period_last_reset"])
        next_reset = temp_parse_timestamp_or_string(restored["period_end"])

        return cls(meter_data, time_window_active, active, last_reset, next_reset)

    @classmethod
    def from_dict(cls, restored: dict[str, Any]) -> MeasureItSensorStoredData:
        """Initialize a stored sensor state from a dict."""
        try:
            if not restored.get("meter_data"):
                return MeasureItSensorStoredData.from_old_format_dict(restored)

            meter_data = restored["meter_data"]
            time_window_active = bool(restored["time_window_active"])
            active = bool(restored["active"])
            last_reset = (
                datetime.fromisoformat(restored["last_reset"]).astimezone(
                    tz=dt_util.DEFAULT_TIME_ZONE
                )
                if restored.get("last_reset")
                else None
            )
            next_reset = (
                datetime.fromisoformat(restored["next_reset"]).astimezone(
                    tz=dt_util.DEFAULT_TIME_ZONE
                )
                if restored.get("next_reset")
                else None
            )
        except KeyError:
            # restored is a dict, but does not have all values
            return None

        return cls(meter_data, time_window_active, active, last_reset, next_reset)


class MeasureItSensor(MeasureItCoordinatorEntity, RestoreEntity, SensorEntity):
    """MeasureIt Sensor Entity."""

    _attr_has_entity_name = True

    def __init__(  # noqa: PLR0913
        self,
        hass: HomeAssistant,
        coordinator: MeasureItCoordinator,
        meter: MeasureItMeter,
        unique_id: str,
        sensor_name: str,
        reset_pattern: str | None,
        value_template_renderer: Callable[[Any], Any],
        state_class: SensorStateClass,
        device_class: SensorDeviceClass | None = None,
        unit_of_measurement: str | None = None,
    ) -> None:
        """Initialize a sensor entity."""
        self.hass = hass
        self._coordinator = coordinator
        self.meter = meter
        self._attr_unique_id = unique_id
        self._attr_name = sensor_name
        self._reset_pattern = reset_pattern
        self._value_template_renderer = value_template_renderer
        self._attr_native_unit_of_measurement = unit_of_measurement

        if state_class and state_class not in [
            SensorStateClass.TOTAL,
            SensorStateClass.TOTAL_INCREASING,
            None,
        ]:
            msg = "Only SensorStateClass TOTAL or none is supported."
            raise TypeError(msg)
        self._attr_state_class = state_class
        self._attr_device_class = device_class

        self._attr_should_poll = False

        self._time_window_active: bool = False
        self._active: bool = False
        self._reset_listener = None
        self._last_reset: datetime = dt_util.now()
        self._next_reset: datetime | None = None

        self.scheduler = None
        if self._reset_pattern not in [
            None,
            "noreset",
            "forever",
            "none",
            "session",
        ]:
            self.scheduler = CronSim(
                self._reset_pattern,
                dt_util.now(dt_util.get_default_time_zone()),
            )

    async def async_added_to_hass(self) -> None:
        """Add sensors as a listener for coordinator updates."""
        if (last_sensor_data := await self.async_get_last_sensor_data()) is not None:
            _LOGGER.debug(
                "%s # Restoring data from last session: %s",
                self._attr_name,
                last_sensor_data,
            )
            self.meter.from_dict(last_sensor_data.meter_data)
            self._active = last_sensor_data.active
            self._time_window_active = last_sensor_data.time_window_active
            self._last_reset = last_sensor_data.last_reset
            self.schedule_next_reset(last_sensor_data.next_reset)
        else:
            _LOGGER.warning("%s # Could not restore data", self._attr_name)
            self.schedule_next_reset()

        self.async_on_remove(self._coordinator.async_register_sensor(self))
        self.async_on_remove(self.unsub_reset_listener)

    @callback
    def calibrate(self, value: Decimal) -> None:
        """Calibrate the meter with a given value."""
        _LOGGER.info("%s # Calibrate with value: %s", self._attr_name, value)
        self.meter.calibrate(Decimal(value))
        self.async_write_ha_state()

    @callback
    def unsub_reset_listener(self) -> None:
        """Unsubscribe and remove the reset listener."""
        if self._reset_listener:
            self._reset_listener()
            self._reset_listener = None

    @property
    def sensor_state(self) -> SensorState:
        """Return the sensor state."""
        if (
            self.meter.meter_type == MeterType.SOURCE
            and not self.meter.has_source_value
        ):
            return SensorState.INITIALIZING_SOURCE
        if self._active is True and self._time_window_active is True:
            return SensorState.MEASURING
        if self._time_window_active is False:
            return SensorState.WAITING_FOR_TIME_WINDOW
        if self._active is False:
            return SensorState.WAITING_FOR_CONDITION
        msg = "Invalid sensor state determined."
        raise ValueError(msg)

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        return self._value_template_renderer(self.meter.measured_value)

    @property
    def prev_native_value(self) -> Decimal | None:
        """Return the state of the sensor."""
        return self._value_template_renderer(self.meter.prev_measured_value)

    @property
    def last_reset(self) -> datetime | None:
        """Return the time when the sensor was last reset, if any."""
        if self.state_class == SensorStateClass.TOTAL:
            return self._last_reset
        return None

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the state attributes."""
        attributes = {
            ATTR_STATUS: self.sensor_state,
            ATTR_PREV: str(
                self._value_template_renderer(self.meter.prev_measured_value)
                # strange things happen when we parse this one as a Decimal...
            ),
            ATTR_LAST_RESET: self._last_reset.isoformat(timespec="seconds")
            if self._last_reset
            else None,
            ATTR_NEXT_RESET: self._next_reset.isoformat(timespec="seconds")
            if self._next_reset
            else None,
        }
        if self.meter.meter_type == MeterType.SOURCE:
            attributes["source_entity"] = self._coordinator.source_entity
        return attributes

    @callback
    def reset(self, event: Event | None = None) -> None:  # noqa: ARG002
        """Reset the sensor."""
        reset_datetime = dt_util.now()
        _LOGGER.info("Resetting sensor %s at %s", self._attr_name, reset_datetime)
        self.meter.reset()
        self._last_reset = reset_datetime

        self.schedule_next_reset()
        self._async_write_ha_state()

    @callback
    def on_reset_service_triggered(
        self, reset_datetime: datetime | None = None
    ) -> None:
        """Handle a reset service call."""
        _LOGGER.debug("Reset sensor with: %s", reset_datetime)
        if reset_datetime is None:
            reset_datetime = dt_util.now()
        if not reset_datetime.tzinfo:
            reset_datetime = reset_datetime.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        self.schedule_next_reset(reset_datetime)

    @callback
    def schedule_next_reset(self, next_reset: datetime | None = None) -> None:
        """Set the next reset moment."""
        tznow = dt_util.now()
        if next_reset and next_reset <= tznow:
            self.reset()
            return
        if not next_reset:
            if self.scheduler:
                while (next_reset := next(self.scheduler)) <= tznow:
                    pass
            else:
                self._next_reset = None
                return

        self._next_reset = next_reset

        if self._reset_listener:
            self._reset_listener()
        self._reset_listener = async_track_point_in_time(
            self.hass,
            self.reset,
            self._next_reset,  # type: ignore[arg-type]
        )

    @callback
    def on_condition_template_change(self, *, active: bool) -> None:
        """Handle a change in the condition template."""
        old_state = self.sensor_state
        self._active = active
        new_state = self.sensor_state
        self._on_sensor_state_update(old_state, new_state)
        self._async_write_ha_state()

    @callback
    def on_time_window_change(self, *, active: bool) -> None:
        """Handle a change in the time window."""
        old_state = self.sensor_state
        self._time_window_active = active
        new_state = self.sensor_state
        self._on_sensor_state_update(old_state, new_state)
        self._async_write_ha_state()

    def source_has_reset(self, new_value: Decimal) -> bool:
        """Check if the source has reset."""
        if self.state_class != SensorStateClass.TOTAL_INCREASING:
            return False
        return new_value < self.meter.measured_value * Decimal("0.9")

    @callback
    def on_value_change(self, new_value: Decimal | None = None) -> None:
        """Handle a change in the value."""
        old_state = self.sensor_state
        if new_value is not None:
            if self.meter.meter_type == MeterType.SOURCE and self.source_has_reset(
                new_value
            ):
                meter: SourceMeter = self.meter
                meter.handle_source_reset(new_value)
            else:
                self.meter.update(new_value)
        else:
            self.meter.update()
        if old_state == SensorState.INITIALIZING_SOURCE:
            new_state = self.sensor_state
            self._on_sensor_state_update(old_state, new_state)
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
            self._async_write_ha_state()
            if self._reset_pattern == "session":
                self.reset()

    @property
    def extra_restore_state_data(self) -> MeasureItSensorStoredData:
        """Return sensor specific state data to be stored."""
        return MeasureItSensorStoredData(
            self.meter.to_dict(),
            self._time_window_active,
            self._active,
            self._last_reset,
            self._next_reset,
        )

    async def async_get_last_sensor_data(self) -> MeasureItSensorStoredData | None:
        """Retrieve sensor data to be restored."""
        if (restored_last_extra_data := await self.async_get_last_extra_data()) is None:
            return None
        return MeasureItSensorStoredData.from_dict(restored_last_extra_data.as_dict())
