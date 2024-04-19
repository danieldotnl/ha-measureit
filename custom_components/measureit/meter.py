"""Meter logic for MeasureIt."""

from datetime import UTC, datetime
from decimal import Decimal

from custom_components.measureit.const import MeterType


class MeasureItMeter:
    """Abstract meter implementation to be derived by concrete meters."""

    _meter_type: MeterType

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

    @property
    def meter_type(self) -> MeterType:
        """Get the meter type."""
        return self._meter_type

    def start(self):
        """Start the meter."""
        raise NotImplementedError()

    def stop(self):
        """Stop the meter."""
        raise NotImplementedError()

    def update(self, value: Decimal | None = None):
        """Update the meter."""
        raise NotImplementedError()

    def calibrate(self, value: Decimal):
        """Calibrate the meter."""
        raise NotImplementedError()

    def reset(self):
        """Reset the meter."""
        raise NotImplementedError()

    def to_dict(self) -> dict:
        """Return the meter as a dictionary."""
        return {
            "measured_value": str(self.measured_value),
            "prev_measured_value": str(self.prev_measured_value),
            "measuring": self.measuring,
        }

    def from_dict(self, data: dict) -> None:
        """Restore the meter from a dictionary."""
        self._measured_value = Decimal(data["measured_value"])
        self._prev_measured_value = Decimal(data["prev_measured_value"])
        self._measuring = bool(data["measuring"])


class CounterMeter(MeasureItMeter):
    """Counter meter implementation."""

    _meter_type = MeterType.COUNTER

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

    def calibrate(self, value: Decimal):
        """Calibrate the meter."""
        self._measured_value = value

    def reset(self):
        """Reset the meter."""
        self._prev_measured_value, self._measured_value = self._measured_value, Decimal(
            0
        )


class SourceMeter(MeasureItMeter):
    """Source meter implementation."""

    _meter_type = MeterType.SOURCE

    def __init__(self):
        """Initialize meter."""
        super().__init__()
        self._session_start_value = Decimal(0)
        self._session_start_measured_value = Decimal(0)
        self._source_value = None

    @property
    def has_source_value(self) -> bool:
        """Check if the meter has a source value."""
        return self._source_value is not None

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
        if value is None:
            raise ValueError("Source meter requires a value to update")
        self._source_value = value
        if self._measuring:
            self._session_total = self._source_value - self._session_start_value
            self._measured_value = (
                self._session_start_measured_value + self._session_total
            )

    def calibrate(self, value: Decimal):
        """Calibrate the meter."""
        self._measured_value = value
        if self._measuring:
            self._session_start_measured_value = value
            # This kind of starts a new session but does not do a reset
            self._session_start_value = self._source_value

    def reset(self):
        """Reset the meter."""
        if self._measuring:
            self.stop()
            self._prev_measured_value = self._measured_value
            self._measured_value = Decimal(0)
            self.start()
        else:
            self._prev_measured_value = self._measured_value
            self._measured_value = Decimal(0)

    def handle_source_reset(self, value: Decimal):
        """Handle source reset."""
        if self._measuring:
            self.stop()
            self._source_value = Decimal(0)
            self.start()
            self.update(value)
        else:
            self._source_value = value

    def to_dict(self) -> dict:
        """Return the meter as a dictionary."""
        data = super().to_dict()
        source_data = {
            **data,
            "session_start_value": str(self._session_start_value),
            "session_start_measured_value": str(self._session_start_measured_value),
        }
        if self._source_value is not None:
            source_data["source_value"] = str(self._source_value)
        return source_data

    def from_dict(self, data: dict) -> None:
        """Restore the meter from a dictionary."""
        super().from_dict(data)
        self._session_start_value = Decimal(data["session_start_value"])
        self._session_start_measured_value = Decimal(
            data["session_start_measured_value"]
        )

        source_value = data.get("source_value")
        self._source_value = Decimal(source_value) if source_value is not None else None


class TimeMeter(MeasureItMeter):
    """Time meter implementation."""

    _meter_type = MeterType.TIME

    def __init__(self):
        """Initialize meter."""
        super().__init__()
        self._session_start_value = Decimal(0)
        self._session_start_measured_value = Decimal(0)

    def get_timestamp(self) -> Decimal:
        """Get timestamp."""
        return Decimal(datetime.now(UTC).timestamp())

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

    def calibrate(self, value: Decimal):
        """Calibrate the meter."""
        self._measured_value = value
        if self._measuring:
            self._session_start_measured_value = value
            # This kind of starts a new session but does not do a reset
            self._session_start_value = self.get_timestamp()

    def reset(self):
        """Reset the meter."""
        if self._measuring:
            self.stop()
            self._prev_measured_value = self._measured_value
            self._measured_value = Decimal(0)
            self.start()
        else:
            self._prev_measured_value = self._measured_value
            self._measured_value = Decimal(0)

    def to_dict(self) -> dict:
        """Return the meter as a dictionary."""
        data = super().to_dict()
        return {
            **data,
            "session_start_value": str(self._session_start_value),
            "session_start_measured_value": str(self._session_start_measured_value),
        }

    def from_dict(self, data: dict) -> None:
        """Restore the meter from a dictionary."""
        super().from_dict(data)
        self._session_start_value = Decimal(data["session_start_value"])
        self._session_start_measured_value = Decimal(
            data["session_start_measured_value"]
        )
