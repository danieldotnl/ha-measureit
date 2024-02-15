"""Test the TimeMeter class."""
from decimal import Decimal
from datetime import datetime, timedelta
from custom_components.measureit.meter import TimeMeter

HOUR = 3600


class DatetimeMock:
    """Mock datetime."""

    def __init__(self, now: datetime, change: timedelta) -> None:
        """Initialize mock."""
        self._now = now
        self._change = change

    def get_timestamp(self) -> Decimal:
        """Get timestamp."""
        self._now = self._now + self._change
        return Decimal(self._now.timestamp())


def test_init():
    """Test initializing a time meter."""
    meter = TimeMeter()
    assert meter.measured_value == Decimal(0)
    assert meter.prev_measured_value == Decimal(0)
    assert meter.measuring is False


def test_start():
    """Test starting a time meter."""
    meter = TimeMeter()
    meter.start()
    assert meter.measuring is True
    assert meter.measured_value == Decimal(0)


def test_stop():
    """Test stopping a time meter."""
    meter = TimeMeter()
    mock = DatetimeMock(datetime.now(), timedelta(hours=1))
    meter.get_timestamp = mock.get_timestamp
    meter.start()
    meter.stop()
    assert meter.measuring is False
    assert meter.measured_value == Decimal(HOUR)


def test_update():
    """Test updating a time meter."""
    meter = TimeMeter()
    mock = DatetimeMock(datetime.now(), timedelta(hours=1))
    meter.get_timestamp = mock.get_timestamp
    meter.start()
    meter.update()
    assert meter.measured_value == Decimal(HOUR)
    meter.update()
    assert meter.measured_value == Decimal(HOUR * 2)
    meter.stop()
    assert meter.measured_value == Decimal(HOUR * 3)
    meter.update()
    assert meter.measured_value == Decimal(HOUR * 3)
    meter.start()
    meter.update()
    assert meter.measured_value == Decimal(HOUR * 4)
    meter.stop()
    assert meter.measured_value == Decimal(HOUR * 5)


def test_reset_when_measuring():
    """Test resetting a time meter when measuring."""
    meter = TimeMeter()
    mock = DatetimeMock(datetime.now(), timedelta(hours=1))
    meter.get_timestamp = mock.get_timestamp

    meter.start()
    meter.update()
    assert meter.measured_value == Decimal(HOUR)
    assert meter.measuring is True
    meter.reset()
    assert meter.measuring is True
    assert meter.measured_value == Decimal(0)
    assert meter.prev_measured_value == Decimal(HOUR * 2)


def test_reset_when_not_measuring():
    """Test resetting a time meter when not measuring."""
    meter = TimeMeter()
    mock = DatetimeMock(datetime.now(), timedelta(hours=1))
    meter.get_timestamp = mock.get_timestamp

    meter.start()
    meter.update()
    meter.stop()
    assert meter.measured_value == Decimal(HOUR * 2)
    meter.reset()
    assert meter.measured_value == Decimal(0)
    assert meter.prev_measured_value == Decimal(HOUR * 2)


def test_store_and_restore():
    """Test storing and restoring a counter meter."""
    meter = TimeMeter()
    mock = DatetimeMock(datetime.now(), timedelta(hours=1))
    meter.get_timestamp = mock.get_timestamp

    meter.start()
    meter.update()
    assert meter.measuring is True
    assert meter.measured_value == Decimal(HOUR)
    data = meter.to_dict()

    meter2 = TimeMeter()
    meter2.get_timestamp = mock.get_timestamp

    meter2.from_dict(data)
    assert meter2.measuring is True
    assert meter2.measured_value == Decimal(HOUR)
    meter2.update()
    meter2.update()
    meter2.stop()
    assert meter2.measuring is False
    assert meter2.measured_value == Decimal(HOUR * 4)
    assert isinstance(meter2.measured_value, Decimal)
    data = meter2.to_dict()

    meter3 = TimeMeter()
    meter3.get_timestamp = mock.get_timestamp
    meter3.from_dict(data)
    assert meter3.measuring is False
    assert meter3.measured_value == Decimal(HOUR * 4)
