"""Time window for MeasureIt."""
from datetime import datetime


class TimeWindow:
    """TimeWindow class with active check."""

    def __init__(self, days: list[str], from_time: str, till_time: str) -> None:
        """Initialize TimeWindow."""
        self.days = [int(day) for day in days]
        self.start = datetime.strptime(from_time, "%H:%M:%S").time()
        self.end = datetime.strptime(till_time, "%H:%M:%S").time()

    def is_active(self, tznow: datetime):
        """Check if a given datetime is inside the time window."""
        check_time = tznow.time()
        if self.start < self.end:
            if check_time >= self.start and check_time <= self.end:
                return tznow.weekday() in self.days
        else:  # crosses midnight
            if check_time >= self.start or check_time <= self.end:
                if check_time < self.start:
                    return prev_weekday(tznow.weekday()) in self.days
                else:
                    return tznow.weekday() in self.days
        return False


def prev_weekday(day: int) -> int:
    """Return the previous weekday."""
    if day == 0:
        return 6
    return day - 1
