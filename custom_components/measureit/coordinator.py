"""Custom oordinator (not derived from the core DataUpdateCoordinator) for the MeasureIt component."""
from __future__ import annotations

import logging
from datetime import datetime
from datetime import timedelta
from typing import Any, get_args
from collections.abc import Callable

import homeassistant.util.dt as dt_util
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import callback
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.event import async_track_template_result
from homeassistant.helpers.event import TrackTemplate
from homeassistant.helpers.template import Template

from .reading import ReadingData

from .time_window import TimeWindow
from .util import NumberType

UPDATE_INTERVAL = timedelta(minutes=1)
_LOGGER: logging.Logger = logging.getLogger(__name__)


class MeasureItCoordinator:
    """MeasureIt Coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_name: str,
        condition: Template | None,
        time_window: TimeWindow,
        value_callback: Callable[[str], NumberType],
    ) -> None:
        """Initialize the coordinator."""
        self._hass: HomeAssistant = hass
        self._name: str = config_name
        self._meters = []
        self._condition: Template | None = condition
        self._get_value: Callable[[str], NumberType] = value_callback
        self._listeners: dict[
            Callable[[ReadingData], None],
            tuple[Callable[[ReadingData], None], object | None],
        ] = {}
        self._time_window: TimeWindow = time_window
        self._template_listener = None
        self._heartbeat_listener = None
        self.last_reading = None

        self._template_active: bool = True

    def stop(self):
        """Stop the coordinator."""
        _LOGGER.debug("Stopping coordinator")
        if self._template_listener:
            self._template_listener.async_remove()
        if self._heartbeat_listener:
            self._heartbeat_listener()

    def start(self):
        """Start the coordinator."""
        if self._condition:
            self._template_listener = async_track_template_result(
                self._hass,
                [TrackTemplate(self._condition, None)],
                self._async_on_template_update,
            )
            self._template_listener.async_refresh()

        self.async_on_heartbeat()

    @callback
    def async_add_listener(
        self, update_callback: Callable[[ReadingData], None], context: Any = None
    ) -> Callable[[], None]:
        """Listen for data updates."""

        @callback
        def remove_listener() -> None:
            """Remove update listener."""
            self._listeners.pop(remove_listener)

        self._listeners[remove_listener] = (update_callback, context)

        if self.last_reading:
            update_callback(self.last_reading)
        return remove_listener

    def _async_on_update(self, event=None):
        tznow = dt_util.now()
        _LOGGER.debug(
            "%s # Update triggered at: %s.",
            self._name,
            tznow.isoformat(),
        )

        try:
            reading_value = self._parse_value(self._get_value())
            self.last_reading = reading_value
        except (ValueError, AttributeError) as ex:
            _LOGGER.error(
                "%s # Could not update meters because the input value is invalid. Error: %s",
                self._name,
                ex,
            )
            # set the input value to the last updated value, so the meters are at least reset when required
            if self.last_reading:
                reading_value = self.last_reading
            else:
                return  # nothing we can do... we'll try again next time

        tw_active = self._time_window.is_active(tznow)
        reading = ReadingData(
            reading_datetime=tznow,
            value=reading_value,
            timewindow_active=tw_active,
            template_active=self._template_active,
        )

        self._update_listeners(reading)

    @callback
    def async_on_heartbeat(self, now: datetime | None = None):
        """Configure the coordinator heartbeat."""
        self._async_on_update()

        # We _floor_ utcnow to create a schedule on a rounded minute,
        # minimizing the time between the point and the real activation.
        # That way we obtain a constant update frequency,
        # as long as the update process takes less than a minute
        self._heartbeat_listener = async_track_point_in_utc_time(
            self._hass,
            self.async_on_heartbeat,
            dt_util.utcnow().replace(second=0, microsecond=0) + UPDATE_INTERVAL,
        )

    @callback
    def _async_on_template_update(self, event, updates):
        result = updates.pop().result

        if isinstance(result, TemplateError):
            _LOGGER.error(
                "%s # Encountered a template error: %s. Could not start or stop measuring!",
                self._name,
                result,
            )
        else:
            _LOGGER.debug("%s # Condition template changed to: %s.", self._name, result)
            self._template_active = result
            self._async_on_update()

    def _update_listeners(self, reading):
        for update_callback, _ in list(self._listeners.values()):
            update_callback(reading)

    def _parse_value(self, value: Any) -> NumberType | None:
        if isinstance(value, get_args(NumberType)):
            return value
        elif value in [STATE_UNKNOWN, STATE_UNAVAILABLE]:
            _LOGGER.debug(
                "%s # Error converting value %s to a number.", self._name, value
            )
            raise ValueError("Could not process value as it's unknown or unavailable.")
        else:
            return float(value)
