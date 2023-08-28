"""Tests for MeasureIt time window class."""

from datetime import datetime

import pytz
from custom_components.measureit.time_window import TimeWindow

TZ = pytz.timezone("Europe/Amsterdam")


def test_active_with_window():
    """Test is_active function time_window class."""
    tw = TimeWindow(["0", "1", "2"], "00:00:00", "02:00:00")

    fake_now = TZ.localize(datetime(2022, 1, 1, 10, 30))  # = saturday
    assert tw.is_active(fake_now) is False

    fake_now = TZ.localize(datetime(2022, 1, 1, 1, 30))  # = saturday
    assert tw.is_active(fake_now) is False

    fake_now = TZ.localize(datetime(2022, 1, 3, 1, 30))  # = monday
    assert tw.is_active(fake_now) is True

    fake_now = TZ.localize(datetime(2022, 1, 3, 3, 30))  # = monday outside tw
    assert tw.is_active(fake_now) is False


def test_tw_cross_midnight():
    """Test is_active function time_window class when time window crosses midnight."""
    tw = TimeWindow(["0"], "22:00:00", "04:00:00")  # monday

    fake_now = TZ.localize(datetime(2022, 1, 1, 10, 30))  # = saturday
    assert tw.is_active(fake_now) is False

    fake_now = TZ.localize(datetime(2022, 1, 3, 23, 30))  # = monday in TW
    assert tw.is_active(fake_now) is True

    fake_now = TZ.localize(datetime(2022, 1, 4, 1, 30))  # = tuesday in TW of monday
    assert tw.is_active(fake_now) is True

    fake_now = TZ.localize(datetime(2022, 1, 3, 1, 30))  # = monday in TW of sunday
    assert tw.is_active(fake_now) is False


def test_cross_midnight_on_sunday():
    """Test is_active function time_window class when time window crosses midnight on first day of week."""
    tw = TimeWindow(["6"], "22:00:00", "04:00:00")  # sunday

    fake_now = TZ.localize(datetime(2022, 1, 2, 23, 30))  # = Sunday in TW
    assert tw.is_active(fake_now) is True

    fake_now = TZ.localize(datetime(2022, 1, 2, 21, 30))  # = Sunday before TW
    assert tw.is_active(fake_now) is False

    fake_now = TZ.localize(datetime(2022, 1, 3, 1, 30))  # = monday in TW of sunday
    assert tw.is_active(fake_now) is True


def test_active_with_equal_window():
    """Test is_active function time_window class when start and end are equal."""
    tw = TimeWindow(
        ["0", "1", "2"], "00:00:00", "00:00:00"
    )  # monday, tuesday, wednesday

    fake_now = TZ.localize(datetime(2022, 1, 3, 1, 30))  # monday in TW
    assert tw.is_active(fake_now) is True

    fake_now = TZ.localize(datetime(2022, 1, 3, 0, 0))  # monday at start TW
    assert tw.is_active(fake_now) is True

    fake_now = TZ.localize(datetime(2022, 1, 6, 0, 0))  # thursday at start TW
    assert tw.is_active(fake_now) is False

    tw = TimeWindow(["6", "5"], "04:00:00", "04:00:00")  # sunday, saturday

    fake_now = TZ.localize(datetime(2022, 1, 1, 4, 0))  # saturday at start TW
    assert tw.is_active(fake_now) is True

    fake_now = TZ.localize(datetime(2022, 1, 2, 4, 0))  # sunday at start TW
    assert tw.is_active(fake_now) is True

    fake_now = TZ.localize(datetime(2022, 1, 3, 4, 00))  # monday at start TW
    assert tw.is_active(fake_now) is False

    fake_now = TZ.localize(datetime(2022, 1, 2, 4, 10))  # monday after start TW
    assert tw.is_active(fake_now) is True
