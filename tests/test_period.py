"""Tests for MeasureIt period class."""

from datetime import datetime
from datetime import timedelta

import pytz
from custom_components.measureit.const import PREDEFINED_PERIODS
from custom_components.measureit.period import Period

TZ = pytz.timezone("Europe/Amsterdam")


def test_init():
    """Test initializing a period."""
    fake_now = datetime(2022, 1, 1, 10, 30)
    tznow = TZ.localize(fake_now)

    # full day period
    start_pattern = PREDEFINED_PERIODS["day"]
    period = Period(start_pattern, tznow)
    assert period.start == TZ.localize(datetime(2022, 1, 1, 0, 0))
    assert period.end == period.start + timedelta(days=1)


def test_update_period():
    """Test updating a period."""
    fake_now = datetime(2022, 1, 1, 10, 30)
    tznow1 = TZ.localize(fake_now)

    start_pattern = PREDEFINED_PERIODS["day"]
    period = Period(start_pattern, tznow1)

    reset_called = False

    def fake_reset(input_value):
        nonlocal reset_called
        reset_called = True
        assert input_value == 123

    # period shouldn't be reset when updated during period
    fake_now = datetime(2022, 1, 1, 11, 30)
    tznow2 = TZ.localize(fake_now)
    period.update(tznow2, fake_reset, 123)
    assert reset_called is False

    # reset period when updated after end time
    reset_called = False
    fake_now = datetime(2022, 1, 2, 13, 30)
    tznow3 = TZ.localize(fake_now)
    period.update(tznow3, fake_reset, 123)
    assert reset_called is True
    assert period.last_reset == tznow3

    # don't reset again when updated after end time
    reset_called = False
    fake_now = datetime(2022, 1, 2, 13, 35)
    tznow4 = TZ.localize(fake_now)
    period.update(tznow4, fake_reset, 123)
    assert period.last_reset == tznow3
    assert reset_called is False
