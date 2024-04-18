"""Test the SourceMeter class."""

from decimal import Decimal

from custom_components.measureit.meter import SourceMeter


def test_init():
    """Test initializing a counter meter."""
    meter = SourceMeter()
    assert meter.measured_value == Decimal(0)
    assert meter.prev_measured_value == Decimal(0)
    assert meter.measuring is False


def test_update_initial_source_value():
    """Test updating a counter meter with an initial source value."""
    meter = SourceMeter()
    assert meter._source_value is None
    meter.update(Decimal(100))
    assert meter._source_value == Decimal(100)


def test_start():
    """Test starting a counter meter."""
    meter = SourceMeter()
    meter.update(Decimal(100))
    meter.start()
    assert meter.measuring is True
    assert meter.measured_value == Decimal(0)


def test_stop():
    """Test stopping a counter meter."""
    meter = SourceMeter()
    meter.update(Decimal(100))
    meter.start()
    meter.stop()
    assert meter.measuring is False
    assert meter.measured_value == Decimal(0)


def test_update():
    """Test updating a counter meter."""
    meter = SourceMeter()
    meter.update(Decimal(100))
    meter.start()
    meter.update(Decimal(200))
    assert meter.measured_value == Decimal(100)
    meter.update(Decimal(300))
    assert meter.measured_value == Decimal(200)
    meter.stop()
    meter.update(Decimal(500))
    assert meter.measured_value == Decimal(200)
    meter.start()
    meter.update(Decimal(1000))
    assert meter.measured_value == Decimal(700)
    meter.stop()
    assert meter.measured_value == Decimal(700)


def test_negative_update():
    """Test updating a counter meter with negative values."""
    meter = SourceMeter()
    meter.update(Decimal(100))
    meter.start()
    meter.update(Decimal(-200))
    assert meter.measured_value == Decimal(-300)
    meter.update(Decimal(200))
    assert meter.measured_value == Decimal(100)
    meter.update(Decimal(150))
    assert meter.measured_value == Decimal(50)
    meter.stop()
    meter.update(Decimal(200))
    assert meter.measured_value == Decimal(50)
    meter.start()
    assert meter.measured_value == Decimal(50.0)
    meter.update(Decimal(0))
    assert meter.measured_value == Decimal(-150)


def test_update_decimal_values():
    """Test updating a counter meter with decimal values."""
    meter = SourceMeter()
    meter.update(Decimal("10.03"))
    meter.update(Decimal("10.75"))
    meter.start()
    assert meter.measured_value == Decimal(0)
    meter.update(Decimal("10.78"))
    assert meter.measured_value == Decimal("0.03")


def test_reset():
    """Test resetting a counter meter."""
    meter = SourceMeter()
    meter.update(Decimal(100))
    meter.start()
    meter.update(Decimal(200))
    assert meter.measured_value == Decimal(100)
    assert meter.measuring is True
    meter.reset()
    assert meter.measuring is True
    assert meter.measured_value == Decimal(0)
    assert meter.prev_measured_value == Decimal(100)
    meter.reset()
    assert meter.measuring is True
    assert meter.measured_value == Decimal(0)
    assert meter.prev_measured_value == Decimal(0)
    meter.update(Decimal(300))
    assert meter.measuring is True
    assert meter.measured_value == Decimal(100)
    meter.stop()
    assert meter.measuring is False
    assert meter.measured_value == Decimal(100)
    meter.reset()
    assert meter.measuring is False
    assert meter.measured_value == Decimal(0)
    assert meter.prev_measured_value == Decimal(100)
    meter.reset()
    assert meter.measuring is False
    assert meter.measured_value == Decimal(0)
    assert meter.prev_measured_value == Decimal(0)


def test_store_and_restore():
    """Test storing and restoring a source meter."""
    meter = SourceMeter()
    meter.update(Decimal(100))
    meter.start()
    meter.update(Decimal(200))
    assert meter.measuring is True
    assert meter.measured_value == Decimal(100)
    data = meter.to_dict()
    meter2 = SourceMeter()
    meter2.from_dict(data)
    meter2.update(Decimal(300))
    assert meter2.measuring is True
    assert meter2.measured_value == Decimal(200)
    meter2.update(Decimal(500))
    meter2.stop()
    assert meter2.measuring is False
    assert meter2.measured_value == Decimal(400)
    data = meter2.to_dict()
    meter3 = SourceMeter()
    meter3.from_dict(data)
    meter3.update(Decimal(500))
    assert meter3.measuring is False
    assert meter3.measured_value == Decimal(400)

def test_calibrate_while_measuring():
    """Test calibrating a source meter while measuring."""
    meter = SourceMeter()
    meter.update(Decimal(100))
    meter.start()
    meter.update(Decimal(200))
    assert meter.measuring is True
    assert meter.measured_value == Decimal(100)
    meter.calibrate(Decimal(95))
    assert meter.measured_value == Decimal(95)
    meter.update(Decimal(300))
    assert meter.measured_value == Decimal(195)
    meter.stop()
    assert meter.measured_value == Decimal(195)
    meter.update(Decimal(400))
    assert meter.measured_value == Decimal(195)
    meter.calibrate(Decimal(90))
    assert meter.measured_value == Decimal(90)
    meter.calibrate(Decimal(85))
    assert meter.measured_value == Decimal(85)
    meter.start()
    meter.update(Decimal(500))
    assert meter.measured_value == Decimal(185)
