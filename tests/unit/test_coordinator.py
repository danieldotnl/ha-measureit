"""Test for the measureit coordinator."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.template import Template
from homeassistant.util import dt as dt_util

from custom_components.measureit.const import MeterType
from custom_components.measureit.coordinator import (
    MeasureItCoordinator,
    MeasureItCoordinatorEntity,
)
from custom_components.measureit.time_window import TimeWindow


@pytest.fixture(name="coordinator")
def fixture_counter_coordinator(hass: HomeAssistant):
    """Fixture for the MeasureItCoordinator class."""
    coordinator = MeasureItCoordinator(
        hass,
        "test",
        MeterType.COUNTER,
        TimeWindow(["0", "1", "2"], "00:00:00", "02:00:00"),
    )
    yield coordinator
    coordinator.stop()


def test_init(coordinator: MeasureItCoordinator) -> None:
    """Test the initialization of the MeasureItCoordinator class."""
    assert coordinator._time_window.days == [0, 1, 2]


def test_init_should_fail(hass: HomeAssistant) -> None:
    """Test the initialization of the MeasureItCoordinator class without timewindow."""
    with pytest.raises(ValueError):
        MeasureItCoordinator(hass, "test", MeterType.COUNTER, None, None)


def test_register_sensor(coordinator: MeasureItCoordinator) -> None:
    """Test the registration of a sensor."""
    sensor = MeasureItCoordinatorEntity()
    coordinator.async_register_sensor(sensor)
    assert len(coordinator._sensors) == 1


def test_unregister_sensor(coordinator: MeasureItCoordinator) -> None:
    """Test the unregistration of a sensor."""
    sensor = MeasureItCoordinatorEntity()
    unregister = coordinator.async_register_sensor(sensor)
    assert len(coordinator._sensors) == 1
    unregister()
    assert len(coordinator._sensors) == 0


def test_call_multiple_registered_sensors(coordinator: MeasureItCoordinator) -> None:
    """Test if the coordinator calls the registered sensors."""
    entity = MeasureItCoordinatorEntity()
    entity.on_condition_template_change = MagicMock()
    unregister = coordinator.async_register_sensor(entity)

    entity2 = MeasureItCoordinatorEntity()
    entity2.on_condition_template_change = MagicMock()
    coordinator.async_register_sensor(entity2)

    assert len(coordinator._sensors) == 2
    for sensor in coordinator._sensors.values():
        sensor.on_condition_template_change(active=True)
    entity.on_condition_template_change.assert_called_with(active=True)
    entity2.on_condition_template_change.assert_called_with(active=True)

    unregister()
    assert len(coordinator._sensors) == 1
    for sensor in coordinator._sensors.values():
        sensor.on_condition_template_change(active=True)
    entity2.on_condition_template_change.assert_called_with(active=True)


def test_async_on_time_window_active_change(coordinator: MeasureItCoordinator) -> None:
    """Test async_on_time_window_active_change."""
    entity = MeasureItCoordinatorEntity()
    entity.on_time_window_change = MagicMock()
    coordinator.async_register_sensor(entity)
    assert coordinator._time_window_listener is None
    coordinator.async_on_time_window_active_change(
        datetime(2022, 1, 1, 10, 30, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    )
    entity.on_time_window_change.assert_called_with(active=False)
    assert coordinator._time_window_listener is not None


def test_async_on_condition_template_update(coordinator: MeasureItCoordinator) -> None:
    """Test async_on_condition_update."""
    entity = MeasureItCoordinatorEntity()
    entity.on_condition_template_change = MagicMock()
    coordinator.async_register_sensor(entity)
    mock_tracktemplateresultinfo = MagicMock()
    mock_tracktemplateresultinfo.result = False
    coordinator.async_on_condition_template_update(None, [mock_tracktemplateresultinfo])
    entity.on_condition_template_change.assert_called_with(active=False)


# rewrite this using propertymock
class StateMock:
    """Mock for the state object."""

    def __init__(self, state: State) -> None:
        """Initialize the state object."""
        self._state = state

    @property
    def state(self):
        """Return the state."""
        return self._state


def test_async_on_source_state_change(coordinator: MeasureItCoordinator) -> None:
    """Test async_on_source_state_change."""
    entity = MeasureItCoordinatorEntity()
    entity.on_value_change = MagicMock()
    coordinator.async_register_sensor(entity)
    event = MagicMock()
    event.data = {"new_state": StateMock(456), "old_state": StateMock(123)}
    coordinator.async_on_source_entity_state_change(event)
    entity.on_value_change.assert_called_with(456)


def test_async_on_source_state_change_with_unknown_state(
    coordinator: MeasureItCoordinator,
) -> None:
    """Test async_on_source_state_change with unknown state."""
    entity = MeasureItCoordinatorEntity()
    entity.on_value_change = MagicMock()
    coordinator.async_register_sensor(entity)
    event = MagicMock()
    event.data = {"new_state": StateMock(STATE_UNKNOWN), "old_state": StateMock(456)}
    coordinator.async_on_source_entity_state_change(event)
    entity.on_value_change.assert_not_called()


def test_async_on_source_state_change_with_no_number(
    coordinator: MeasureItCoordinator,
) -> None:
    """Test async_on_source_state_change with unknown state."""
    entity = MeasureItCoordinatorEntity()
    entity.on_value_change = MagicMock()
    coordinator.async_register_sensor(entity)
    event = MagicMock()
    event.data = {"new_state": StateMock("test"), "old_state": StateMock(456)}
    coordinator.async_on_source_entity_state_change(event)
    entity.on_value_change.assert_not_called()


def test_async_on_counter_template_update_becomes_true(
    coordinator: MeasureItCoordinator,
) -> None:
    """Test async_on_counter_template_changed."""
    entity = MeasureItCoordinatorEntity()
    entity.on_value_change = MagicMock()
    coordinator.async_register_sensor(entity)
    coordinator.async_on_counter_template_update(
        "mock", StateMock(False), StateMock(True)
    )
    entity.on_value_change.assert_called_with(1)


def test_async_on_heartbeat(coordinator: MeasureItCoordinator) -> None:
    """Test async_on_heartbeat."""
    entity = MeasureItCoordinatorEntity()
    entity.on_value_change = MagicMock()
    coordinator.async_register_sensor(entity)
    assert coordinator._heartbeat_listener is None
    with patch("homeassistant.helpers.event.async_track_point_in_utc_time"):
        coordinator.async_on_heartbeat()

    # sensors are called on heartbeat
    entity.on_value_change.assert_called()

    # next heartbeat has been set
    assert coordinator._heartbeat_listener is not None


def test_start_with_counter(coordinator: MeasureItCoordinator) -> None:
    """Test start."""
    coordinator._condition_template = Template("{{ True }}", coordinator.hass)
    coordinator._counter_template = Template("{{ True }}", coordinator.hass)
    assert coordinator._condition_template_listener is None
    assert coordinator._time_window_listener is None
    assert coordinator._condition_template_listener is None
    coordinator.start()
    assert coordinator._counter_template_listener is not None
    assert coordinator._time_window_listener is not None
    assert coordinator._condition_template_listener is not None


def test_start_with_source(coordinator: MeasureItCoordinator) -> None:
    """Test start."""
    coordinator._meter_type = MeterType.SOURCE
    coordinator._condition_template = Template("{{ True }}", coordinator.hass)
    coordinator._source_entity = "sensor.test"
    coordinator._get_sensor_state = MagicMock(return_value=123)
    entity = MeasureItCoordinatorEntity()
    entity.on_condition_template_change = MagicMock()
    entity.on_value_change = MagicMock()
    entity.on_time_window_change = MagicMock()
    coordinator.async_register_sensor(entity)
    assert coordinator._condition_template_listener is None
    assert coordinator._time_window_listener is None
    assert coordinator._source_entity_update_listener is None
    coordinator.start()
    assert coordinator._source_entity_update_listener is not None
    assert coordinator._time_window_listener is not None
    assert coordinator._condition_template_listener is not None
    entity.on_value_change.assert_called_with(123)


def test_start_with_time(coordinator: MeasureItCoordinator) -> None:
    """Test start."""
    coordinator._meter_type = MeterType.TIME
    coordinator._condition_template = Template("{{ True }}", coordinator.hass)
    assert coordinator._condition_template_listener is None
    assert coordinator._time_window_listener is None
    assert coordinator._heartbeat_listener is None
    coordinator.start()
    assert coordinator._heartbeat_listener is not None
    assert coordinator._time_window_listener is not None
    assert coordinator._condition_template_listener is not None
