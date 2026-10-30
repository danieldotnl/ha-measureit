"""Tests for MeasureIt time window class."""

from datetime import datetime

import pytest
from homeassistant.util import dt as dt_util

from custom_components.measureit.time_window import TimeWindow

TZ = dt_util.DEFAULT_TIME_ZONE


def test_init_time_window() -> None:
    """Test the initialization of the TimeWindow class."""
    tw = TimeWindow(["0", "1", "2"], "00:00:00", "02:00:00")
    assert tw.days == [0, 1, 2]
    assert tw.start == datetime.strptime("00:00:00", "%H:%M:%S").time()
    assert tw.end == datetime.strptime("02:00:00", "%H:%M:%S").time()


def test_init_time_window_always_active() -> None:
    """Test the initialization of the TimeWindow class when always active."""
    tw = TimeWindow(["0", "1", "2", "3", "4", "5", "6"], "00:00:00", "00:00:00")
    assert tw.always_active is True


def test_init_time_window_not_always_active() -> None:
    """Test the initialization of the TimeWindow class when not always active."""
    tw = TimeWindow(["0", "1", "2"], "00:00:00", "02:00:00")
    assert tw.always_active is False


def test_init_with_invalid_days() -> None:
    """Test the initialization of the TimeWindow class with invalid days."""
    with pytest.raises(ValueError):
        TimeWindow(["8"], "00:00:00", "02:00:00")
    with pytest.raises(ValueError):
        TimeWindow(["0", "1", "2", "2"], "00:00:00", "02:00:00")


def test_active_with_window() -> None:
    """Test is_active function time_window class."""
    tw = TimeWindow(["0", "1", "2"], "00:00:00", "02:00:00")

    fake_now = datetime(2022, 1, 1, 10, 30, tzinfo=TZ)  # = saturday
    assert tw.is_active(fake_now) is False

    fake_now = datetime(2022, 1, 1, 1, 30, tzinfo=TZ)  # = saturday
    assert tw.is_active(fake_now) is False

    fake_now = datetime(2022, 1, 3, 1, 30, tzinfo=TZ)  # = monday
    assert tw.is_active(fake_now) is True

    fake_now = datetime(2022, 1, 3, 3, 30, tzinfo=TZ)  # = monday outside tw
    assert tw.is_active(fake_now) is False

    fake_now = datetime(2022, 1, 3, 0, 0, tzinfo=TZ)  # = monday
    assert tw.is_active(fake_now) is True  # TW should be active at start second

    fake_now = datetime(2022, 1, 3, 2, 0, tzinfo=TZ)  # = monday
    assert (
        tw.is_active(fake_now) is False
    )  # TW should not be active anymore at end second


def test_tw_cross_midnight() -> None:
    """Test is_active function time_window class when time window crosses midnight."""
    tw = TimeWindow(["0"], "22:00:00", "04:00:00")  # monday

    fake_now = datetime(2022, 1, 1, 10, 30, tzinfo=TZ)  # = saturday
    assert tw.is_active(fake_now) is False

    fake_now = datetime(2022, 1, 3, 23, 30, tzinfo=TZ)  # = monday in TW
    assert tw.is_active(fake_now) is True

    fake_now = datetime(2022, 1, 4, 1, 30, tzinfo=TZ)  # = tuesday in TW of monday
    assert tw.is_active(fake_now) is True

    fake_now = datetime(2022, 1, 3, 1, 30, tzinfo=TZ)  # = monday in TW of sunday
    assert tw.is_active(fake_now) is False


def test_tw_cross_midnight_end_exclusive() -> None:
    """Test is_active is False exactly at the end of a time window crossing midnight."""
    tw = TimeWindow(["0"], "22:00:00", "04:00:00")  # monday

    fake_now = datetime(2022, 1, 3, 21, 59, 59, tzinfo=TZ)  # = monday before TW
    assert tw.is_active(fake_now) is False

    fake_now = datetime(2022, 1, 3, 22, 0, tzinfo=TZ)  # = monday at start of TW
    assert tw.is_active(fake_now) is True

    fake_now = datetime(2022, 1, 4, 3, 59, 59, tzinfo=TZ)  # = tuesday in TW of monday
    assert tw.is_active(fake_now) is True

    fake_now = datetime(2022, 1, 4, 4, 0, tzinfo=TZ)  # = tuesday at end of TW
    assert tw.is_active(fake_now) is False


def test_tw_ending_at_midnight() -> None:
    """Test is_active when the time window ends at midnight."""
    tw = TimeWindow(["0"], "22:00:00", "00:00:00")  # monday

    fake_now = datetime(2022, 1, 3, 23, 59, 59, tzinfo=TZ)  # = monday in TW
    assert tw.is_active(fake_now) is True

    fake_now = datetime(2022, 1, 4, 0, 0, tzinfo=TZ)  # = tuesday at end of TW
    assert tw.is_active(fake_now) is False

    fake_now = datetime(2022, 1, 4, 10, 0, tzinfo=TZ)  # = tuesday after TW
    assert tw.is_active(fake_now) is False


def test_cross_midnight_on_sunday() -> None:
    """Test is_active() on time_window when it crosses midnight on first day of week."""
    tw = TimeWindow(["6"], "22:00:00", "04:00:00")  # sunday

    fake_now = datetime(2022, 1, 2, 23, 30, tzinfo=TZ)  # = Sunday in TW
    assert tw.is_active(fake_now) is True

    fake_now = datetime(2022, 1, 2, 21, 30, tzinfo=TZ)  # = Sunday before TW
    assert tw.is_active(fake_now) is False

    fake_now = datetime(2022, 1, 3, 1, 30, tzinfo=TZ)  # = monday in TW of sunday
    assert tw.is_active(fake_now) is True


def test_active_with_equal_window() -> None:
    """Test is_active function time_window class when start and end are equal."""
    tw = TimeWindow(
        ["0", "1", "2"], "00:00:00", "00:00:00"
    )  # monday, tuesday, wednesday

    fake_now = datetime(2022, 1, 3, 1, 30, tzinfo=TZ)  # monday in TW
    assert tw.is_active(fake_now) is True

    fake_now = datetime(2022, 1, 3, 0, 0, tzinfo=TZ)  # monday at start TW
    assert tw.is_active(fake_now) is True

    fake_now = datetime(2022, 1, 6, 0, 0, tzinfo=TZ)  # thursday at start TW
    assert tw.is_active(fake_now) is False

    tw = TimeWindow(["6", "5"], "04:00:00", "04:00:00")  # sunday, saturday

    fake_now = datetime(2022, 1, 1, 4, 0, tzinfo=TZ)  # saturday at start TW
    assert tw.is_active(fake_now) is True

    fake_now = datetime(2022, 1, 2, 4, 0, tzinfo=TZ)  # sunday at start TW
    assert tw.is_active(fake_now) is True

    fake_now = datetime(2022, 1, 3, 4, 0, tzinfo=TZ)  # monday at start TW
    assert tw.is_active(fake_now) is False

    fake_now = datetime(2022, 1, 2, 4, 10, tzinfo=TZ)  # monday after start TW
    assert tw.is_active(fake_now) is True


def test_active_when_always_active() -> None:
    """Test is_active when time window is always active."""
    tw = TimeWindow(
        ["0", "1", "2", "3", "4", "5", "6"],
        "00:00:00",
        "00:00:00",
    )
    fake_now = datetime(2022, 1, 3, 4, 0, tzinfo=TZ)  # monday at start TW
    assert tw.is_active(fake_now) is True


def test_next_change_active_to_inactive() -> None:
    """Test next_change when the TimeWindow changes from active to inactive."""
    # TimeWindow active on Mondays (0) from 09:00 to 17:00
    tw = TimeWindow(days=["0"], from_time="09:00:00", till_time="17:00:00")
    # Current time is Monday at 10:00, within the active window
    current_time = datetime(2023, 4, 3, 10, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    # Expect the next change to be the same day at 17:00
    expected_change = datetime(2023, 4, 3, 17, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    assert tw.next_change(current_time) == expected_change


def test_next_change_inactive_to_active() -> None:
    """Test next_change when the TimeWindow changes from inactive to active."""
    # TimeWindow active on Mondays (0) from 09:00 to 17:00
    tw = TimeWindow(days=["0"], from_time="09:00:00", till_time="17:00:00")
    # Current time is Sunday at 20:00, outside the active window
    current_time = datetime(2023, 4, 2, 20, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    # Expect the next change to be the next day (Monday) at 09:00
    expected_change = datetime(2023, 4, 3, 9, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    assert tw.next_change(current_time) == expected_change


def test_next_change_crosses_midnight() -> None:
    """Test next_change when the TimeWindow crosses midnight."""
    # TimeWindow active on Fridays (4) from 22:00 to 02:00 (crosses midnight)
    tw = TimeWindow(days=["4"], from_time="22:00:00", till_time="02:00:00")
    # Current time is Friday at 23:00, within the active window
    current_time = datetime(2023, 4, 7, 23, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    # Expect the next change to be the same day (technically Saturday) at 02:00
    expected_change = datetime(2023, 4, 8, 2, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    assert tw.next_change(current_time) == expected_change


def test_next_change_crosses_midnight_inactive() -> None:
    """Test next_change when TimeWindow crosses midnight and is currently inactive."""
    # TimeWindow active on Fridays (4) from 22:00 to 02:00 (crosses midnight)
    tw = TimeWindow(days=["4"], from_time="22:00:00", till_time="02:00:00")
    # Current time is Saturday at 03:00, outside the active window
    current_time = datetime(2023, 4, 8, 3, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    # Expect the next change to be the next Friday at 22:00
    expected_change = datetime(2023, 4, 14, 22, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    assert tw.next_change(current_time) == expected_change


def test_next_change_crosses_midnight_at_end() -> None:
    """Test next_change exactly at the end of a TimeWindow crossing midnight."""
    # TimeWindow active on all days from 22:00 to 07:00 (crosses midnight)
    tw = TimeWindow(
        days=["0", "1", "2", "3", "4", "5", "6"],
        from_time="22:00:00",
        till_time="07:00:00",
    )
    # Current time is Wednesday at 07:00, the scheduled end of the window
    current_time = datetime(2023, 4, 5, 7, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    # Expect the next change to be the same day at 22:00, not tomorrow at 07:00
    expected_change = datetime(2023, 4, 5, 22, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    assert tw.is_active(current_time) is False
    assert tw.next_change(current_time) == expected_change


def test_next_change_ending_at_midnight() -> None:
    """Test next_change exactly at the end of a TimeWindow ending at midnight."""
    # TimeWindow active on all days from 18:00 to 00:00
    tw = TimeWindow(
        days=["0", "1", "2", "3", "4", "5", "6"],
        from_time="18:00:00",
        till_time="00:00:00",
    )
    # Current time is Tuesday at 00:00, the scheduled end of Monday's window
    current_time = datetime(2023, 4, 4, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    # Expect the next change to be the same day at 18:00, not tomorrow at 00:00
    expected_change = datetime(2023, 4, 4, 18, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    assert tw.is_active(current_time) is False
    assert tw.next_change(current_time) == expected_change

    # TimeWindow active on Mondays (0) from 22:00 to 00:00
    tw = TimeWindow(days=["0"], from_time="22:00:00", till_time="00:00:00")
    # Expect the next change to be the next Monday at 22:00
    expected_change = datetime(2023, 4, 10, 22, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    assert tw.is_active(current_time) is False
    assert tw.next_change(current_time) == expected_change


def test_next_change_full_days() -> None:
    """Test next_change for a 00:00 - 00:00 TimeWindow on part of the week."""
    # TimeWindow active the whole day on Mondays (0) and Tuesdays (1)
    tw = TimeWindow(days=["0", "1"], from_time="00:00:00", till_time="00:00:00")

    # Sunday at 23:59:59: inactive, next change is Monday at 00:00
    current_time = datetime(2023, 4, 2, 23, 59, 59, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    assert tw.is_active(current_time) is False
    assert tw.next_change(current_time) == datetime(
        2023, 4, 3, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )

    # Monday at 00:00: active, next change is Tuesday at 00:00
    current_time = datetime(2023, 4, 3, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    assert tw.is_active(current_time) is True
    assert tw.next_change(current_time) == datetime(
        2023, 4, 4, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )

    # Tuesday at 00:00: still active, next change is Wednesday at 00:00
    current_time = datetime(2023, 4, 4, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    assert tw.is_active(current_time) is True
    assert tw.next_change(current_time) == datetime(
        2023, 4, 5, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )

    # Tuesday at 23:59:59: still active, next change is Wednesday at 00:00
    current_time = datetime(2023, 4, 4, 23, 59, 59, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    assert tw.is_active(current_time) is True
    assert tw.next_change(current_time) == datetime(
        2023, 4, 5, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )

    # Wednesday at 00:00: inactive, next change is the next Monday at 00:00
    current_time = datetime(2023, 4, 5, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    assert tw.is_active(current_time) is False
    assert tw.next_change(current_time) == datetime(
        2023, 4, 10, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )


def test_next_change_starting_at_midnight() -> None:
    """Test next_change for a TimeWindow starting at midnight."""
    # TimeWindow active on Mondays (0) from 00:00 to 02:00
    tw = TimeWindow(days=["0"], from_time="00:00:00", till_time="02:00:00")

    # Sunday at 23:00: inactive, next change is Monday at 00:00
    current_time = datetime(2023, 4, 2, 23, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    assert tw.is_active(current_time) is False
    assert tw.next_change(current_time) == datetime(
        2023, 4, 3, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )

    # Monday at 00:00: active, next change is Monday at 02:00
    current_time = datetime(2023, 4, 3, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    assert tw.is_active(current_time) is True
    assert tw.next_change(current_time) == datetime(
        2023, 4, 3, 2, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )

    # Monday at 02:00: inactive, next change is the next Monday at 00:00
    current_time = datetime(2023, 4, 3, 2, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    assert tw.is_active(current_time) is False
    assert tw.next_change(current_time) == datetime(
        2023, 4, 10, 0, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )


def test_next_change_crosses_new_week() -> None:
    """Test next_change when the TimeWindow crosses into a new week."""
    # TimeWindow active on Mondays (0) from 09:00 to 17:00
    tw = TimeWindow(days=["0"], from_time="09:00:00", till_time="17:00:00")
    # Current time is Sunday at 23:00, outside the active window
    current_time = datetime(2023, 4, 2, 23, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    # Expect the next change to be the next day (Monday) at 09:00
    expected_change = datetime(2023, 4, 3, 9, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    assert tw.next_change(current_time) == expected_change


def test_next_change_always_active() -> None:
    """Test next_change when the TimeWindow is always active."""
    tw = TimeWindow(
        days=["0", "1", "2", "3", "4", "5", "6"],
        from_time="00:00:00",
        till_time="00:00:00",
    )
    # Current time is Sunday at 23:00, inside the active window
    current_time = datetime(2023, 4, 1, 23, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    with pytest.raises(AssertionError):
        tw.next_change(current_time)
