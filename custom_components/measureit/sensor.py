"""Sensor platform for MeasureIt."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import voluptuous as vol
from croniter import croniter
from dateutil import tz
from homeassistant.components.sensor import (SensorDeviceClass, SensorEntity,
                                             SensorStateClass)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (ATTR_ENTITY_ID, CONF_DEVICE_CLASS,
                                 CONF_UNIQUE_ID, CONF_UNIT_OF_MEASUREMENT,
                                 CONF_VALUE_TEMPLATE)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform
from homeassistant.helpers.config_validation import make_entity_service_schema
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.restore_state import ExtraStoredData, RestoreEntity
from homeassistant.util import dt as dt_util

from .const import (ATTR_LAST_RESET, ATTR_NEXT_RESET, ATTR_PREV, ATTR_STATUS,
                    CONF_CONFIG_NAME, CONF_CRON, CONF_METER_TYPE, CONF_SENSOR,
                    CONF_SENSOR_NAME, CONF_STATE_CLASS, COORDINATOR,
                    DOMAIN_DATA, EVENT_TYPE_RESET, MeterType, SensorState)
from .coordinator import MeasureItCoordinator, MeasureItCoordinatorEntity
from .meter import CounterMeter, MeasureItMeter, SourceMeter, TimeMeter
from .util import create_renderer

_LOGGER: logging.Logger = logging.getLogger(__name__)


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
            value_template_renderer = create_renderer(hass, sensor.get(CONF_VALUE_TEMPLATE), 3)
        elif meter_type == MeterType.COUNTER:
            meter = CounterMeter()
            value_template_renderer = create_renderer(hass, sensor.get(CONF_VALUE_TEMPLATE))
        elif meter_type == MeterType.TIME:
            meter = TimeMeter()
            value_template_renderer = create_renderer(hass, sensor.get(CONF_VALUE_TEMPLATE), 0)
        else:
            _LOGGER.error("%s # Invalid meter type: %s", config_name, meter_type)
            raise ValueError(f"Invalid meter type: {meter_type}")



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
                    vol.Required("value"): cv.Number
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
        "on_reset_service_triggered"
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
    condition_active: bool
    last_reset: datetime | None
    next_reset: datetime | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a dict representation of the meter data."""

        _LOGGER.debug("Persisting meter data")

        data = {
            "meter_data": self.meter_data,
            "time_window_active": self.time_window_active,
            "condition_active": self.condition_active,
            "last_reset": self.last_reset.isoformat() if self.last_reset else None,
            "next_reset": self.next_reset.isoformat() if self.next_reset else None,
        }
        return data

    @classmethod
    def from_old_format_dict(
        cls, restored: dict[str, Any]
    ) -> MeasureItSensorStoredData:
        """Initialize a stored sensor state from an old format dict."""
        time_window_active = False
        condition_active = False
        if restored.get("state") == SensorState.MEASURING:
            time_window_active = True
            condition_active = True
        elif restored.get("state") == SensorState.WAITING_FOR_TIME_WINDOW:
            time_window_active = False
            condition_active = True
        elif restored.get("state") == SensorState.WAITING_FOR_CONDITION:
            time_window_active = True
            condition_active = False
        meter_data = {
            "measured_value": restored["measured_value"],
            "session_start_value": restored["session_start_reading"],
            "session_start_measured_value": restored["start_measured_value"],
            "prev_measured_value": restored["prev_measured_value"],
            "measuring": True if restored["state"] == SensorState.MEASURING else False,
        }
        if meter_data["session_start_value"] is None:
            meter_data["session_start_value"] = 0
        if meter_data["session_start_measured_value"] is None:
            meter_data["session_start_measured_value"] = 0

        last_reset = temp_parse_timestamp_or_string(restored["period_last_reset"])
        next_reset = temp_parse_timestamp_or_string(restored["period_end"])

        return cls(
            meter_data, time_window_active, condition_active, last_reset, next_reset
        )

    @classmethod
    def from_dict(cls, restored: dict[str, Any]) -> MeasureItSensorStoredData:
        """Initialize a stored sensor state from a dict."""

        try:
            if not restored.get("meter_data"):
                return MeasureItSensorStoredData.from_old_format_dict(restored)

            meter_data = restored["meter_data"]
            time_window_active = bool(restored["time_window_active"])
            condition_active = bool(restored["condition_active"])
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

        return cls(
            meter_data, time_window_active, condition_active, last_reset, next_reset
        )


class MeasureItSensor(MeasureItCoordinatorEntity, RestoreEntity, SensorEntity):
    """MeasureIt Sensor Entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: MeasureItCoordinator,
        meter: MeasureItMeter,
        unique_id: str,
        sensor_name: str,
        reset_pattern: str | None,
        value_template_renderer,
        state_class: SensorStateClass,
        device_class: SensorDeviceClass | None = None,
        unit_of_measurement: str | None = None,
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

        if state_class and state_class not in [
            SensorStateClass.TOTAL,
            SensorStateClass.TOTAL_INCREASING,
            None,
        ]:
            raise TypeError("Only SensorStateClass TOTAL or none is supported.")
        self._attr_state_class = state_class
        self._attr_device_class = device_class

        self._attr_should_poll = False
        self._set_translation_key()

        self._time_window_active: bool = False
        self._condition_active: bool = False
        self._reset_listener = None
        self._last_reset: datetime = dt_util.now()
        self._next_reset: datetime | None = None

    async def async_added_to_hass(self):
        """Add sensors as a listener for coordinator updates."""

        if (last_sensor_data := await self.async_get_last_sensor_data()) is not None:
            _LOGGER.debug(
                "%s # Restoring data from last session: %s",
                self._attr_name,
                last_sensor_data,
            )
            self.meter.from_dict(last_sensor_data.meter_data)
            self._condition_active = last_sensor_data.condition_active
            self._time_window_active = last_sensor_data.time_window_active
            self._last_reset = last_sensor_data.last_reset
            self.schedule_next_reset(last_sensor_data.next_reset)
        else:
            _LOGGER.warning("%s # Could not restore data", self._attr_name)
            self.schedule_next_reset()

        self.async_on_remove(self._coordinator.async_register_sensor(self))
        self.async_on_remove(self.unsub_reset_listener)

        @callback
        def event_filter(event_data: Mapping[str, Any] | Event):
            """Filter events."""

            # Breaking change in 2024.4.0, check for Event for versions prior to this
            if type(event_data) is Event:  # Intentionally avoid `isinstance` because it's slow and we trust `Event` is not subclassed
                event_data = event_data.data
            return self.entity_id in event_data.get(ATTR_ENTITY_ID)

        @callback
        def on_reset_event(event):
            self.schedule_next_reset(event.data.get("reset_datetime"))

        self.async_on_remove(
            self.hass.bus.async_listen(EVENT_TYPE_RESET, on_reset_event, event_filter)
        )

    @callback
    def calibrate(self, value):
        """Calibrate the meter with a given value."""
        _LOGGER.info("%s # Calibrate with value: %s", self._attr_name, value)
        self.meter.calibrate(Decimal(value))
        self.async_write_ha_state()

    @callback
    def unsub_reset_listener(self):
        """Unsubscribe and remove the reset listener."""
        if self._reset_listener:
            self._reset_listener()
            self._reset_listener = None

    @property
    def sensor_state(self) -> SensorState:
        """Return the sensor state."""
        if self.meter.meter_type == MeterType.SOURCE and not self.meter.has_source_value:
            return SensorState.INITIALIZING_SOURCE
        if self._condition_active is True and self._time_window_active is True:
            return SensorState.MEASURING
        elif self._time_window_active is False:
            return SensorState.WAITING_FOR_TIME_WINDOW
        elif self._condition_active is False:
            return SensorState.WAITING_FOR_CONDITION
        else:
            raise ValueError("Invalid sensor state determined.")

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

    def _set_translation_key(self) -> None:
        """Set the translation key."""
        if self.meter.meter_type == MeterType.SOURCE:
            self._attr_translation_key = "source-meter"
        elif self.meter.meter_type == MeterType.TIME:
            self._attr_translation_key = "time-meter"
        elif self.meter.meter_type == MeterType.COUNTER:
            self._attr_translation_key = "counter-meter"

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the state attributes."""
        attributes = {
            ATTR_STATUS: self.sensor_state,
            ATTR_PREV: str(  # strange things happen when we parse this one as a Decimal...
                self._value_template_renderer(self.meter.prev_measured_value)
            ),
            ATTR_LAST_RESET: self._last_reset.isoformat(timespec="seconds") if self._last_reset else None,
            ATTR_NEXT_RESET: self._next_reset.isoformat(timespec="seconds") if self._next_reset else None,
        }
        if self.meter.meter_type == MeterType.SOURCE:
            attributes["source_entity"] = self._coordinator.source_entity
        return attributes

    @callback
    def reset(self, event=None):
        """Reset the sensor."""
        reset_datetime = dt_util.now()
        _LOGGER.info("Resetting sensor %s at %s", self._attr_name, reset_datetime)
        self.meter.reset()
        self._last_reset = reset_datetime

        self.schedule_next_reset()
        self._async_write_ha_state()

    @callback
    def on_reset_service_triggered(self, reset_datetime: datetime|None = None):
        """Handle a reset service call."""
        _LOGGER.debug("Reset sensor with: %s", reset_datetime)
        if reset_datetime is None:
            reset_datetime = dt_util.now()
        if not reset_datetime.tzinfo:
            reset_datetime = reset_datetime.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        self.schedule_next_reset(reset_datetime)

    @callback
    def schedule_next_reset(self, next_reset: datetime | None = None):
        """Set the next reset moment."""
        tznow = dt_util.now()
        if next_reset and next_reset <= tznow:
            self.reset()
            return
        elif not next_reset:
            if self._reset_pattern not in [None, "noreset", "forever", "none", "session"]:
                # we have a known issue with croniter that does not correctly determine the end of the month/week reset when DST is involved
                # https://github.com/kiorky/croniter/issues/1
                next_reset = dt_util.as_local(croniter(self._reset_pattern, tznow.replace(tzinfo=None)).get_next(datetime))
                if not tz.datetime_exists(next_reset):
                    next_reset = dt_util.as_local(croniter(self._reset_pattern, next_reset.replace(tzinfo=None)).get_next(datetime))
            else:
                self._next_reset = None
                return

        self._next_reset = next_reset
        if self._reset_listener:
            self._reset_listener()
        self._reset_listener = async_track_point_in_time(
            self.hass,
            self.reset,
            self._next_reset,  # type: ignore
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

    def source_has_reset(self, new_value: Decimal) -> bool:
        """Check if the source has reset."""
        if self.state_class != SensorStateClass.TOTAL_INCREASING:
            return False
        return new_value < self.meter.measured_value * Decimal('0.9')

    @callback
    def on_value_change(self, new_value: Decimal | None = None) -> None:
        """Handle a change in the value."""
        old_state = self.sensor_state
        if new_value is not None:
            if self.meter.meter_type == MeterType.SOURCE and self.source_has_reset(new_value):
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
            self._condition_active,
            self._last_reset,
            self._next_reset,
        )

    async def async_get_last_sensor_data(self) -> MeasureItSensorStoredData | None:
        """Retrieve sensor data to be restored."""
        if (restored_last_extra_data := await self.async_get_last_extra_data()) is None:
            return None
        return MeasureItSensorStoredData.from_dict(restored_last_extra_data.as_dict())
