"""Meter logic for MeasureIt."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from homeassistant.util import dt as dt_util

from .period import Period

# import logging
# _LOGGER: logging.Logger = logging.getLogger(__package__)


class MeterState(str, Enum):
    """Enum with possible meter states."""

    MEASURING = "measuring"
    WAITING_FOR_CONDITION = "waiting for condition"
    WAITING_FOR_TIME_WINDOW = "waiting for time window"


class Meter:
    """Meter implementation."""

    def __init__(self, name: str, period: Period):
        """Initialize meter."""
        self.name = name
        self._period = period

        self.state: MeterState | None = None
        self.measured_value = 0
        self.prev_measured_value = 0
        self._session_start_reading: float | None = None
        self._start_measured_value: float | None = None

        self._template_active: bool = False
        self._time_window_active: bool = False

    @property
    def last_reset(self):
        """Last reset property."""
        return self._period.last_reset

    @property
    def next_reset(self):
        """Next reset property."""
        return self._period.end

    def disable_template(self):
        """Disable template for meter."""
        # TODO: check what's going on here and why it's called disable while setting to True
        self._template_active = True  # bit hacky but more explicit than setting _template_active from coordinator

    def on_heartbeat(self, tznow: datetime, reading: float, tw_active: bool):
        """Define what happens on heartbeat."""
        if self.state == MeterState.MEASURING:
            self._update(reading)
        self._period.update(tznow, self._reset, reading)
        self._time_window_active = tw_active
        self._update_state(reading)

    def on_template_change(
        self, tznow: datetime, reading: float, tp_active: bool, tw_active: bool
    ):
        """Define what happens on a template change."""
        if self.state == MeterState.MEASURING:
            self._update(reading)
        self._period.update(tznow, self._reset, reading)
        self._template_active = tp_active
        self._time_window_active = tw_active
        self._update_state(reading)

    def _update_state(self, reading: float) -> MeterState:
        if self._template_active is True and self._time_window_active is True:
            new_state = MeterState.MEASURING
        elif self._time_window_active is False:
            new_state = MeterState.WAITING_FOR_TIME_WINDOW
        elif self._template_active is False:
            new_state = MeterState.WAITING_FOR_CONDITION
        else:
            raise ValueError("Invalid state determined.")

        if new_state == self.state:
            return
        if new_state == MeterState.MEASURING:
            self._start(reading)
        self.state = new_state

    def _start(self, reading):
        self._session_start_reading = reading
        self._start_measured_value = self.measured_value

    def _update(self, reading: float):
        session_value = reading - self._session_start_reading
        self.measured_value = self._start_measured_value + session_value

    def _reset(self, reading):
        self.prev_measured_value, self.measured_value = self.measured_value, 0
        self._session_start_reading = reading
        self._start_measured_value = self.measured_value

    @classmethod
    def to_dict(cls, meter: Meter) -> dict[str, str]:
        """Convert meter to dictionary."""
        data = {
            "measured_value": meter.measured_value,
            "start_measured_value": meter._start_measured_value,
            "prev_measured_value": meter.prev_measured_value,
            "session_start_reading": meter._session_start_reading,
            "last_reset": dt_util.as_timestamp(meter._period.last_reset),
            "state": meter.state,
        }
        return data

    @classmethod
    def from_dict(cls, data: dict[str, str], meter: Meter) -> Meter:
        """Convert dictionary to meter."""
        meter.measured_value = data["measured_value"]
        meter._start_measured_value = data["start_measured_value"]
        meter.prev_measured_value = data["prev_measured_value"]
        meter._session_start_reading = data["session_start_reading"]
        last_reset = data.get("last_reset")
        if last_reset:
            meter._period.last_reset = dt_util.utc_from_timestamp(last_reset)
        meter.state = MeterState(data["state"])

        return meter
