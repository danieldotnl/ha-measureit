"""Tests for MeasureIt meter class."""

from datetime import datetime

import pytest
import pytz
from custom_components.measureit.meter import Meter
from custom_components.measureit.meter import MeterState
from custom_components.measureit.period import Period
from custom_components.measureit.reading import ReadingData
from custom_components.measureit.sensor import MeasureItMeterStoredData

START_PATTERN = "0 0 * * *"
NAME = "24h"
TZ = pytz.timezone("Europe/Amsterdam")


@pytest.fixture
def meter():
    """Create a fixture for testing meter class."""
    fake_now = datetime(2022, 1, 1, 10, 30)
    period = Period(START_PATTERN, tznow=TZ.localize(fake_now))
    return Meter(NAME, period)


def test_init(meter: Meter):
    """Test initializing a meter."""
    start = datetime(2022, 1, 1, 0, 0)
    assert meter._period.start == TZ.localize(start)


def test_heartbeat(meter: Meter):
    """Test on_heartbeat function of meter."""
    # should trigger meter start()
    reading = ReadingData(
        reading_datetime=TZ.localize(datetime(2022, 1, 1, 11, 5)),
        value=123,
        template_active=True,
        timewindow_active=True,
    )
    meter.on_update(reading)
    assert meter._session_start_reading == 123
    assert meter._start_measured_value == 0

    fake_now = TZ.localize(datetime(2022, 1, 1, 11, 10))
    meter.on_update(ReadingData(fake_now, True, True, 130))
    assert meter.measured_value == 7

    # next day, meter should reset
    fake_now = TZ.localize(datetime(2022, 1, 2, 11, 11))
    meter.on_update(ReadingData(fake_now, True, True, 132))
    assert meter.measured_value == 0
    assert meter.prev_measured_value == 9

    fake_now = TZ.localize(datetime(2022, 1, 2, 11, 20))
    meter.on_update(ReadingData(fake_now, True, False, 140))
    assert meter.measured_value == 8

    fake_now = TZ.localize(datetime(2022, 1, 2, 11, 20))
    meter.on_update(ReadingData(fake_now, True, False, 145))
    assert meter.measured_value == 8

    fake_now = TZ.localize(datetime(2022, 1, 2, 11, 20))
    meter.on_update(ReadingData(fake_now, True, True, 148))
    assert meter.measured_value == 8

    fake_now = TZ.localize(datetime(2022, 1, 2, 11, 21))
    meter.on_update(ReadingData(fake_now, True, True, 150))
    assert meter.measured_value == 10


def test_template_update(meter: Meter):
    """Test on_template_change function of meter."""
    fake_now = TZ.localize(datetime(2022, 1, 1, 11, 5))
    meter.on_update(ReadingData(fake_now, True, True, 123))
    assert meter.state == MeterState.MEASURING

    fake_now = TZ.localize(datetime(2022, 1, 1, 11, 6))
    meter.on_update(ReadingData(fake_now, False, True, 125))
    assert meter.state == MeterState.WAITING_FOR_CONDITION
    assert meter.measured_value == 2

    fake_now = TZ.localize(datetime(2022, 1, 1, 11, 7))
    meter.on_update(ReadingData(fake_now, True, True, 127))
    assert meter.state == MeterState.MEASURING
    assert meter.measured_value == 2

    fake_now = TZ.localize(datetime(2022, 1, 1, 11, 8))
    meter.on_update(ReadingData(fake_now, True, True, 130))
    assert meter.state == MeterState.MEASURING
    assert meter.measured_value == 5


# def test_daylight_savings(meter):
#     fake_now = datetime(2022, 3, 27, 1, 50, tzinfo=timezone.utc)  # start summer time
#     meter.start(fake_now.timestamp())

#     fake_now += timedelta(minutes=20)  # 2:10
#     meter.stop(fake_now.timestamp())

#     assert meter._box_state == 1200

#     fake_reset = datetime(2022, 10, 30, 2, 50, tzinfo=pytz.timezone("Europe/Amsterdam"))
#     fake_now = datetime(2022, 10, 30, 2, 50, tzinfo=timezone.utc)  # start winter time
#     meter = Meter(NAME, reset_pattern=RESET_PATTERN, tznow=fake_reset)
#     meter.start(fake_now.timestamp())

#     fake_now = datetime(2022, 10, 30, 3, 10, tzinfo=timezone.utc)  # 2:10
#     meter.stop(fake_now.timestamp())

#     assert meter._box_state == 1200


def test_update_after_restore(meter: Meter):
    """Test restoring a meter after serialization."""
    fake_now = TZ.localize(datetime(2022, 1, 1, 10, 35))
    meter.on_update(ReadingData(fake_now, True, True, 100))
    assert meter.measured_value == 0
    assert meter.state == MeterState.MEASURING

    fake_now = TZ.localize(datetime(2022, 1, 1, 23, 35))
    meter.on_update(ReadingData(fake_now, True, True, 250))
    assert meter.measured_value == 150

    restore = MeasureItMeterStoredData(
        meter.state,
        meter.measured_value,
        meter.prev_measured_value,
        meter._session_start_reading,
        meter._start_measured_value,
        meter._period.last_reset,
        meter._period.end,
    ).as_dict()

    assert restore["measured_value"] == 150

    last_meter_data = MeasureItMeterStoredData.from_dict(restore)

    # restore is after the end of the period so meter needs to be reset
    fake_now = datetime(2022, 1, 2, 0, 30)
    period = Period(START_PATTERN, tznow=TZ.localize(fake_now))
    meter2 = Meter(NAME, period)

    meter2.state = last_meter_data.state
    meter2.measured_value = last_meter_data.measured_value
    meter2._start_measured_value = last_meter_data.start_measured_value
    meter2.prev_measured_value = last_meter_data.prev_measured_value
    meter2._session_start_reading = last_meter_data.session_start_reading
    meter2._period.last_reset = last_meter_data.period_last_reset
    meter2._period.end = last_meter_data.period_end

    assert meter2.measured_value == 150

    fake_now = TZ.localize(datetime(2022, 1, 2, 0, 35))
    meter2.on_update(ReadingData(fake_now, True, True, 350))
    assert meter2.measured_value == 0
    assert meter2.prev_measured_value == 250
