"""
Custom coordinator for the MeasureIt component.

Note that this coordinator is not derived from the core DataUpdateCoordinator.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.event import (
    TrackTemplate,
    TrackTemplateResult,
    TrackTemplateResultInfo,
    async_track_point_in_time,
    async_track_point_in_utc_time,
    async_track_state_change_event,
    async_track_template,
    async_track_template_result,
)
from homeassistant.util import dt as dt_util

from .const import MeterType

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.helpers.template import Template

    from .time_window import TimeWindow

UPDATE_INTERVAL = timedelta(minutes=1)
_LOGGER: logging.Logger = logging.getLogger(__name__)


class MeasureItCoordinator:
    """MeasureIt Coordinator."""

    def __init__(  # noqa: PLR0913
        self,
        hass: HomeAssistant,
        config_name: str,
        meter_type: MeterType,
        time_window: TimeWindow,
        condition_template: Template | None = None,
        counter_template: Template | None = None,
        source_entity: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        self.hass: HomeAssistant = hass
        self._config_name: str = config_name

        if meter_type is None:
            msg = "Meter type must be provided."
            raise ValueError(msg)
        self._meter_type: MeterType = meter_type

        if time_window is None:
            msg = "Time window must be provided."
            raise ValueError(msg)
        self._time_window: TimeWindow = time_window

        self._condition_template: Template | None = condition_template
        self._counter_template: Template | None = counter_template
        self._source_entity: str | None = source_entity

        self._sensors: dict[Callable, MeasureItCoordinatorEntity] = {}
        self._time_window_listener: Callable | None = None
        self._condition_template_listener: TrackTemplateResultInfo | None = None
        self._counter_template_listener: Callable | None = None
        self._source_entity_update_listener: Callable | None = None
        self._heartbeat_listener: Callable | None = None

    @property
    def source_entity(self) -> str | None:
        """Return the source entity."""
        return self._source_entity

    @callback
    def async_register_sensor(
        self, sensor: MeasureItCoordinatorEntity
    ) -> Callable[[], None]:
        """Register a sensor with the coordinator."""

        @callback
        def unregister_sensor() -> None:
            """Unregister the sensor."""
            self._sensors.pop(unregister_sensor)

        self._sensors[unregister_sensor] = sensor
        return unregister_sensor

    def _get_sensor_state(self, entity_id: str) -> Any:
        """Get the state of a sensor."""
        state = self.hass.states.get(entity_id)
        if state is not None:
            return state.state
        return None

    def start(self) -> None:
        """Start the coordinator."""
        tznow = dt_util.now()

        if self._meter_type == MeterType.SOURCE:
            self._setup_source_meter()
        elif self._meter_type == MeterType.COUNTER:
            self._setup_counter_meter()
        elif self._meter_type == MeterType.TIME:
            self._setup_time_meter()

        if self._time_window.always_active:
            time_window_active = True
        else:
            self._time_window_listener = async_track_point_in_time(
                self.hass,
                self.async_on_time_window_active_change,
                self._time_window.next_change(tznow),
            )
            time_window_active = self._time_window.is_active(tznow)
        for sensor in self._sensors.values():
            sensor.on_time_window_change(active=time_window_active)

        if self._condition_template:
            self._condition_template_listener = async_track_template_result(
                self.hass,
                [TrackTemplate(self._condition_template, None)],
                self.async_on_condition_template_update,
            )
            self._condition_template_listener.async_refresh()
        else:
            _LOGGER.debug(
                """%s # No condition template in configuration
                 so we set the condition to True.""",
                self._config_name,
            )
            for sensor in self._sensors.values():
                sensor.on_condition_template_change(active=True)

    def _setup_source_meter(self) -> None:
        """Set up source meter."""
        if not self._source_entity:
            msg = "Source entity is required for source meters."
            raise AssertionError(msg)
        self._source_entity_update_listener = async_track_state_change_event(
            self.hass,
            self._source_entity,
            self.async_on_source_entity_state_change,
        )
        source_state = self._get_sensor_state(self._source_entity)
        if source_state in [STATE_UNKNOWN, STATE_UNAVAILABLE, None]:
            _LOGGER.warning(
                """%s # Source (%s) state is unknown or unavailable. We cannot start
                 measuring until the source entity has a valid state.""",
                self._config_name,
                self._source_entity,
            )

        try:
            new_state = Decimal(source_state)
            for sensor in self._sensors.values():
                sensor.on_value_change(new_state)
        except (InvalidOperation, TypeError):
            _LOGGER.warning(
                """%s # Could not convert source state to a number: %s. Make sure
                 the source sensor is available and numeric. We cannot start
                 measuring until the source entity has a valid state.""",
                self._config_name,
                source_state,
                exc_info=True,
            )

    def _setup_counter_meter(self) -> None:
        """Set up counter meter."""
        if not self._counter_template:
            msg = "Counter template is required for counter meters."
            raise AssertionError(msg)
        self._counter_template_listener = async_track_template(
            self.hass,
            self._counter_template,
            self.async_on_counter_template_update,
        )

    def _setup_time_meter(self) -> None:
        """Set up time meter."""
        self.async_on_heartbeat()

    def stop(self) -> None:
        """Stop the coordinator."""
        _LOGGER.debug("Stopping coordinator")
        if self._time_window_listener:
            self._time_window_listener()
        if self._condition_template_listener:
            self._condition_template_listener.async_remove()
        if self._counter_template_listener:
            self._counter_template_listener()
        if self._heartbeat_listener:
            self._heartbeat_listener()
        if self._source_entity_update_listener:
            self._source_entity_update_listener()

    @callback
    def async_on_time_window_active_change(self, now: datetime) -> None:
        """Check if the time window is active and update the listeners."""
        _LOGGER.debug(
            "%s # Time window active change triggered at: %s. Next change: %s",
            self._config_name,
            now.isoformat(),
            self._time_window.next_change(now).isoformat(),
        )
        active = self._time_window.is_active(now)
        for sensor in self._sensors.values():
            sensor.on_time_window_change(active=active)

        self._time_window_listener = async_track_point_in_time(
            self.hass,
            self.async_on_time_window_active_change,
            self._time_window.next_change(now),
        )

    @callback
    def async_on_condition_template_update(
        self,
        event: Event,  # noqa: ARG002
        updates: list[TrackTemplateResult],
    ) -> None:
        """Handle changes in the condition template."""
        result = updates.pop().result

        if isinstance(result, TemplateError):
            _LOGGER.error(
                """%s # Encountered a template error: %s.
                 Could not start or stop measuring!""",
                self._config_name,
                result,
            )
        else:
            _LOGGER.debug(
                "%s # Condition template changed to: %s.", self._config_name, result
            )
            for sensor in self._sensors.values():
                sensor.on_condition_template_change(active=bool(result))

    @callback
    def async_on_source_entity_state_change(self, event: Event) -> None:
        """Handle changes in the source entity state."""
        old_state = (
            event.data.get("old_state").state if event.data.get("old_state") else None
        )
        new_state = (
            event.data.get("new_state").state if event.data.get("new_state") else None
        )
        _LOGGER.debug(
            "%s # Source (%s) state changed, old: %s, new: %s",
            self._config_name,
            self._source_entity,
            old_state,
            new_state,
        )
        if new_state in [STATE_UNKNOWN, STATE_UNAVAILABLE, None]:
            _LOGGER.warning(
                """%s # Source (%s) state changed to unknown or unavailable.
                We cannot update the sensors.""",
                self._config_name,
                self._source_entity,
            )
            return

        try:
            new_state = Decimal(new_state)
            for sensor in self._sensors.values():
                sensor.on_value_change(new_state)
        except (InvalidOperation, TypeError):
            _LOGGER.warning(
                """%s # Could not convert source state to a number: %s.
                 Make sure the source sensor is numeric.""",
                self._config_name,
                new_state,
                exc_info=True,
            )

    @callback
    def async_on_counter_template_update(
        self, entity_id: str, old_state: State | None, new_state: State | None
    ) -> None:
        """Handle changes in the counter template."""
        # this function is only called when the counter template became True
        _LOGGER.debug(
            "%s # Counter template changed from %s to %s due to change of: %s.",
            self._config_name,
            old_state.state,
            new_state.state,
            entity_id,
        )
        for sensor in self._sensors.values():
            sensor.on_value_change(Decimal(1))

    @callback
    def async_on_heartbeat(self, now: datetime | None = None) -> None:  # noqa: ARG002
        """Configure the coordinator heartbeat."""
        for sensor in self._sensors.values():
            sensor.on_value_change()

        # We _floor_ utcnow to create a schedule on a rounded minute,
        # minimizing the time between the point and the real activation.
        # That way we obtain a constant update frequency,
        # as long as the update process takes less than a minute
        self._heartbeat_listener = async_track_point_in_utc_time(
            self.hass,
            self.async_on_heartbeat,
            dt_util.utcnow().replace(second=0, microsecond=150) + UPDATE_INTERVAL,
        )


class MeasureItCoordinatorEntity:
    """Coordinator entity for the MeasureIt component."""

    @callback
    def on_condition_template_change(self, *, active: bool) -> None:
        """Abstract method for handling changes in the condition template."""
        msg = "Entity should implement on_condition_template_change()"
        raise NotImplementedError(msg)

    @callback
    def on_time_window_change(self, *, active: bool) -> None:
        """Abstract method for handling changes in the time window."""
        msg = "Entity should implement on_time_window_change()"
        raise NotImplementedError(msg)

    @callback
    def on_value_change(self, new_value: Decimal | None = None) -> None:
        """Abstract method for handling changes in the value."""
        msg = "Entity should implement on_value_change()"
        raise NotImplementedError(msg)
