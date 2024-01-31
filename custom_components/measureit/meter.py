"""Meter logic for MeasureIt."""
from decimal import Decimal
from datetime import datetime


class MeasureItMeter:
    """Abstract meter implementation to be derived by concrete meters."""

    def __init__(self) -> None:
        """Initialize meter."""
        self._measured_value = Decimal(0)
        self._prev_measured_value = Decimal(0)
        self._measuring: bool = False

    @property
    def measured_value(self) -> Decimal:
        """Get the measured value."""
        return self._measured_value

    @property
    def prev_measured_value(self) -> Decimal:
        """Get the previous measured value."""
        return self._prev_measured_value

    @property
    def measuring(self) -> bool:
        """Get the measuring state."""
        return self._measuring

    def start(self):
        """Start the meter."""
        raise NotImplementedError()

    def stop(self):
        """Stop the meter."""
        raise NotImplementedError()

    def update(self, value: Decimal | None = None):
        """Update the meter."""
        raise NotImplementedError()

    def reset(self):
        """Reset the meter."""
        raise NotImplementedError()


class CounterMeter(MeasureItMeter):
    """Counter meter implementation."""

    def __init__(self):
        """Initialize meter."""
        super().__init__()

    def start(self):
        """Start the meter."""
        self._measuring = True

    def stop(self):
        """Stop the meter."""
        self._measuring = False

    def update(self, value: Decimal | None = None):
        """Update the meter."""
        if self._measuring:
            self._measured_value += value

    def reset(self):
        """Reset the meter."""
        self._prev_measured_value, self._measured_value = self._measured_value, Decimal(
            0
        )


class SourceMeter(MeasureItMeter):
    """Source meter implementation."""

    def __init__(self, source_value: Decimal):
        """Initialize meter."""
        super().__init__()
        self._session_start_value = Decimal(0)
        self._session_start_measured_value = Decimal(0)
        self._source_value = source_value

    def start(self):
        """Start the meter."""
        self._measuring = True
        self._session_start_value = self._source_value
        self._session_start_measured_value = self.measured_value

    def stop(self):
        """Stop the meter."""
        self._measuring = False
        self._session_total = self._source_value - self._session_start_value
        self._measured_value = self._session_start_measured_value + self._session_total

    def update(self, value: Decimal | None = None):
        """Update the meter."""
        self._source_value = value
        if self._measuring:
            self._session_total = self._source_value - self._session_start_value
            self._measured_value = (
                self._session_start_measured_value + self._session_total
            )

    def reset(self):
        """Reset the meter."""
        if self._measuring:
            self.stop()
            (
                self._prev_measured_value,
                self._measured_value,
            ) = self._measured_value, Decimal(0)
            self.start()
        else:
            (
                self._prev_measured_value,
                self._measured_value,
            ) = self._measured_value, Decimal(0)


class TimeMeter(MeasureItMeter):
    """Time meter implementation."""

    def __init__(self):
        """Initialize meter."""
        super().__init__()
        self._session_start_value = Decimal(0)
        self._session_start_measured_value = Decimal(0)

    def get_timestamp(self) -> Decimal:
        """Get timestamp."""
        return Decimal(datetime.utcnow().timestamp())

    def start(self):
        """Start the meter."""
        self._measuring = True
        self._session_start_value = self.get_timestamp()
        self._session_start_measured_value = self.measured_value

    def stop(self):
        """Stop the meter."""
        self._measuring = False
        self._session_total = self.get_timestamp() - self._session_start_value
        self._measured_value = self._session_start_measured_value + self._session_total

    def update(self, value: Decimal | None = None):
        """Update the meter."""
        if self._measuring:
            self._session_total = self.get_timestamp() - self._session_start_value
            self._measured_value = (
                self._session_start_measured_value + self._session_total
            )

    def reset(self):
        """Reset the meter."""
        if self._measuring:
            self.stop()
        self._prev_measured_value, self._measured_value = self._measured_value, Decimal(
            0
        )
        if self._measuring:
            self.start()
