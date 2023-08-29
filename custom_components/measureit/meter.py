"""Meter logic for MeasureIt."""
from __future__ import annotations
from enum import Enum
from .reading import ReadingData
from .period import Period
from .const import LOGGER


class MeterState(str, Enum):
    """Enum with possible meter states."""

    MEASURING = "measuring"
    WAITING_FOR_CONDITION = "waiting for condition"
    WAITING_FOR_TIME_WINDOW = "waiting for time window"


class Meter:
    """Meter implementation."""

    def __init__(self, name: str, period: Period):
        """Initialize meter."""
        self.name: str = name
        self._period: Period = period

        self.state: MeterState | None = None
        self.measured_value: float = 0
        self.prev_measured_value: float = 0
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

    def on_update(self, reading: ReadingData):
        """Define what happens on a template change."""
        if self.state == MeterState.MEASURING:
            self._update(reading.value)
        self._period.update(reading.reading_datetime, self._reset, reading.value)
        self._template_active = reading.template_active
        self._time_window_active = reading.timewindow_active
        self._update_state(reading.value)

        LOGGER.debug(
            "New state - measured value: %s, start_measured_value: %s, session_start_reading: %s, state: %s",
            self.measured_value,
            self._start_measured_value,
            self._session_start_reading,
            self.state,
        )

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
