"""Test the CounterMeter class."""
from decimal import Decimal
from custom_components.measureit.meter import CounterMeter


def test_init():
    """Test initializing a counter meter."""
    meter = CounterMeter()
    assert meter.measured_value == Decimal(0)
    assert meter.prev_measured_value == Decimal(0)
    assert meter.measuring is False


def test_start():
    """Test starting a counter meter."""
    meter = CounterMeter()
    meter.start()
    assert meter.measuring is True
    assert meter.measured_value == Decimal(0)


def test_stop():
    """Test stopping a counter meter."""
    meter = CounterMeter()
    meter.start()
    meter.stop()
    assert meter.measuring is False
    assert meter.measured_value == Decimal(0)


def test_update():
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


def test_reset_when_measuring():
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


def test_reset_when_not_measuring():
    """Test resetting a counter meter when not measuring."""
    meter = CounterMeter()
    meter.start()
    meter.update(1)
    meter.stop()
    meter.reset()
    assert meter.measured_value == Decimal(0)
    assert meter.prev_measured_value == Decimal(1)
