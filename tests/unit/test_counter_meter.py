"""Test the CounterMeter class."""

from decimal import Decimal

from custom_components.measureit.meter import CounterMeter


def test_init() -> None:
    """Test initializing a counter meter."""
    meter = CounterMeter()
    assert meter.measured_value == Decimal(0)
    assert meter.prev_measured_value == Decimal(0)
    assert meter.measuring is False


def test_start() -> None:
    """Test starting a counter meter."""
    meter = CounterMeter()
    meter.start()
    assert meter.measuring is True
    assert meter.measured_value == Decimal(0)


def test_stop() -> None:
    """Test stopping a counter meter."""
    meter = CounterMeter()
    meter.start()
    meter.stop()
    assert meter.measuring is False
    assert meter.measured_value == Decimal(0)


def test_update() -> None:
    """Test updating a counter meter."""
    meter = CounterMeter()
    meter.start()
    meter.update(1)
    assert meter.measured_value == Decimal(1)
    meter.update(Decimal(1))
    assert meter.measured_value == Decimal(2)
    meter.stop()
    meter.update(1)
    assert meter.measured_value == Decimal(2)
    meter.start()
    meter.update(2)
    assert meter.measured_value == Decimal(4)
    meter.stop()
    assert meter.measured_value == Decimal(4)


def test_reset_when_measuring() -> None:
    """Test resetting a counter meter when measuring."""
    meter = CounterMeter()
    meter.start()
    meter.update(1)
    meter.reset()
    assert meter.measured_value == Decimal(0)
    assert meter.prev_measured_value == Decimal(1)
    meter.reset()
    assert meter.measured_value == Decimal(0)
    assert meter.prev_measured_value == Decimal(0)


def test_reset_when_not_measuring() -> None:
    """Test resetting a counter meter when not measuring."""
    meter = CounterMeter()
    meter.start()
    meter.update(1)
    meter.stop()
    meter.reset()
    assert meter.measured_value == Decimal(0)
    assert meter.prev_measured_value == Decimal(1)


def test_store_and_restore() -> None:
    """Test storing and restoring a counter meter."""
    meter = CounterMeter()
    meter.start()
    meter.update(1)
    assert meter.measuring is True
    assert meter.measured_value == Decimal(1)
    data = meter.to_dict()
    meter2 = CounterMeter()
    meter2.from_dict(data)
    assert meter2.measuring is True
    assert meter2.measured_value == Decimal(1)
    meter2.update(1)
    meter2.stop()
    assert meter2.measuring is False
    assert meter2.measured_value == Decimal(2)
    data = meter2.to_dict()
    meter3 = CounterMeter()
    meter3.from_dict(data)
    assert meter3.measuring is False
    assert meter3.measured_value == Decimal(2)


def test_calibrate() -> None:
    """Test calibrating a counter meter while measuring."""
    meter = CounterMeter()
    meter.start()
    meter.update(1)
    assert meter.measured_value == Decimal(1)
    meter.calibrate(2)
    assert meter.measured_value == Decimal(2)
    meter.update(1)
    assert meter.measured_value == Decimal(3)
    meter.stop()
    meter.calibrate(2)
    assert meter.measured_value == Decimal(2)
    meter.start()
    meter.update(1)
    assert meter.measured_value == Decimal(3)
    meter.calibrate(2)
    assert meter.measured_value == Decimal(2)
    meter.stop()
    assert meter.measured_value == Decimal(2)
