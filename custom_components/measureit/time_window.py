"""Time window class for active check and next change time."""

from datetime import datetime, time, timedelta

NOF_WEEKDAYS = 7


class TimeWindow:
    """TimeWindow class with active check and next change time."""

    def __init__(self, days: list[str], from_time: str, till_time: str) -> None:
        """Initialize TimeWindow."""
        if len(days) != len(set(days)):
            msg = "Duplicate days are not allowed."
            raise ValueError(msg)
        if len(days) == 0:
            msg = "At least one day must be provided."
            raise ValueError(msg)

        self._days = [int(day) for day in days]
        for day in self._days:
            if day < 0 or day > NOF_WEEKDAYS - 1:
                msg = "Invalid day provided."
                raise ValueError(msg)

        self._start = datetime.strptime(from_time, "%H:%M:%S").time()  # noqa: DTZ007
        self._end = datetime.strptime(till_time, "%H:%M:%S").time()  # noqa: DTZ007

        self._always_active = (
            len(self._days) == NOF_WEEKDAYS
            and self._start == time(0, 0)
            and self._end == time(0, 0)
        )

    @property
    def days(self) -> list[int]:
        """Return the days the time window is active."""
        return self._days

    @property
    def start(self) -> time:
        """Return the start time of the time window."""
        return self._start

    @property
    def end(self) -> time:
        """Return the end time of the time window."""
        return self._end

    @property
    def always_active(self) -> bool:
        """Return if the time window is always active."""
        return self._always_active

    def is_active(self, tznow: datetime) -> bool:
        """Check if a given datetime is inside the time window."""
        if self._always_active:
            return True
        check_time = tznow.time()
        if self._start < self._end:
            if check_time >= self._start and check_time < self._end:
                return tznow.weekday() in self._days
        elif check_time >= self._start or check_time <= self._end:
            if check_time < self._start:
                return prev_weekday(tznow.weekday()) in self._days
            return tznow.weekday() in self._days
        return False

    def next_change(self, tznow: datetime) -> datetime:
        """Return the next time the time window will change state."""
        if self._always_active:
            msg = """Next change should not be called
                for time windows that are always active."""
            raise AssertionError(msg)
        if self.is_active(tznow):
            # If currently active, find the end time today or on the next day
            if tznow.time() < self._end:
                # End time is today
                return datetime.combine(tznow.date(), self._end, tznow.tzinfo)
            # End time is tomorrow
            return datetime.combine(
                tznow.date() + timedelta(days=1), self._end, tznow.tzinfo
            )
        # If currently inactive, find the start time today or the next active day
        if tznow.time() < self._start and tznow.weekday() in self._days:
            # Start time is today
            return datetime.combine(tznow.date(), self._start, tznow.tzinfo)
        # Find the next active day
        next_active_date = self._find_next_active_day(tznow)
        return datetime.combine(next_active_date, self._start, tznow.tzinfo)

    def _find_next_active_day(self, tznow: datetime) -> datetime.date:
        """Find the next active day."""
        for days_ahead in range(1, 8):  # Check the next 7 days
            next_day = tznow + timedelta(days=days_ahead)
            if next_day.weekday() in self._days:
                return next_day.date()
        msg = "Invalid time window, could not find the next active day."
        raise ValueError(msg)


def prev_weekday(day: int) -> int:
    """Return the previous weekday."""
    if day == 0:
        return 6
    return day - 1
