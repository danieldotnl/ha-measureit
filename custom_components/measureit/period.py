"""Period logic for MeasureIt."""
from __future__ import annotations

from datetime import datetime
from collections.abc import Callable

from croniter import croniter


class Period:
    """Implement a Period."""

    def __init__(self, start_pattern: str, tznow: datetime) -> None:
        """Initialize period."""
        self._start_pattern: str = start_pattern
        self.start: datetime = croniter(self._start_pattern, tznow).get_prev(datetime)
        self.end: datetime = self._determine_end()
        self.last_reset: datetime = tznow

    def update(self, tznow: datetime, reset_func: Callable, input_value: float):
        """Update a period with the current time."""
        if self.end <= tznow:
            self.last_reset = tznow
            self.start = self.end
            self.end = self._determine_end()
            reset_func(input_value)

    def _determine_end(self) -> datetime:
        return croniter(self._start_pattern, self.start).get_next(datetime)
