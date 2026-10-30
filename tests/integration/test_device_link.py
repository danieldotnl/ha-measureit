"""Test linking MeasureIt sensors to a device."""

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.measureit.const import DOMAIN
from tests import setup_with_mock_config, unload_with_mock_config

SENSORS = [
    {
        "state_class": "total",
        "unique_id": "ca100892-b6bb-11ee-923e-0242ac110010",
        "sensor_name": "day",
        "cron": "0 0 * * *",
        "period": "day",
    },
]


def create_device(hass: HomeAssistant, name: str) -> dr.DeviceEntry:
    """Create a device that belongs to another integration."""
    device_config_entry = MockConfigEntry(domain="test")
    device_config_entry.add_to_hass(hass)
    return dr.async_get(hass).async_get_or_create(
        config_entry_id=device_config_entry.entry_id,
        identifiers={("test", name)},
        name=name,
    )


def create_source_entry(options: dict | None = None) -> MockConfigEntry:
    """Create a source meter config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        options={
            "config_name": "test",
            "meter_type": "source",
            "source_entity": "sensor.test_source",
            "when_days": ["0", "1", "2", "3", "4", "5", "6"],
            "when_from": "00:00:00",
            "when_till": "00:00:00",
            "sensor": SENSORS,
            **(options or {}),
        },
    )


def create_time_entry(options: dict | None = None) -> MockConfigEntry:
    """Create a time meter config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        options={
            "config_name": "test",
            "meter_type": "time",
            "when_days": ["0", "1", "2", "3", "4", "5", "6"],
            "when_from": "00:00:00",
            "when_till": "00:00:00",
            "sensor": SENSORS,
            **(options or {}),
        },
    )


def get_sensor_entity_id(hass: HomeAssistant) -> str:
    """Return the entity id of the MeasureIt sensor."""
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, SENSORS[0]["unique_id"]
    )
    assert entity_id
    return entity_id


def get_sensor_device_id(hass: HomeAssistant) -> str | None:
    """Return the device id of the MeasureIt sensor."""
    entry = er.async_get(hass).async_get(get_sensor_entity_id(hass))
    assert entry
    return entry.device_id


def register_source_entity(hass: HomeAssistant, device: dr.DeviceEntry) -> None:
    """Register the source entity on the given device."""
    er.async_get(hass).async_get_or_create(
        "sensor",
        "test",
        "source",
        suggested_object_id="test_source",
        device_id=device.id,
    )
    hass.states.async_set("sensor.test_source", "3")


async def test_source_meter_without_device_is_not_linked(hass: HomeAssistant) -> None:
    """Test a source meter with the device cleared is not linked to the source."""
    source_device = create_device(hass, "source_device")
    register_source_entity(hass, source_device)
    entry = create_source_entry()

    await setup_with_mock_config(hass, entry)

    assert get_sensor_device_id(hass) is None
    await unload_with_mock_config(hass, entry)


async def test_selected_device_overrides_source_device(hass: HomeAssistant) -> None:
    """Test a selected device takes precedence over the source entity's device."""
    source_device = create_device(hass, "source_device")
    selected_device = create_device(hass, "selected_device")
    register_source_entity(hass, source_device)
    entry = create_source_entry({"device_id": selected_device.id})

    await setup_with_mock_config(hass, entry)

    assert get_sensor_device_id(hass) == selected_device.id
    await unload_with_mock_config(hass, entry)


async def test_source_meter_without_source_device(hass: HomeAssistant) -> None:
    """Test a source meter is not linked when the source entity has no device."""
    hass.states.async_set("sensor.test_source", "3")
    entry = create_source_entry()

    await setup_with_mock_config(hass, entry)

    assert get_sensor_device_id(hass) is None
    await unload_with_mock_config(hass, entry)


async def test_time_meter_links_to_selected_device(hass: HomeAssistant) -> None:
    """Test a time meter links to the selected device."""
    device = create_device(hass, "selected_device")
    entry = create_time_entry({"device_id": device.id})

    await setup_with_mock_config(hass, entry)

    assert get_sensor_device_id(hass) == device.id
    await unload_with_mock_config(hass, entry)


async def test_linked_sensor_is_named_after_device(hass: HomeAssistant) -> None:
    """Test a linked sensor gets the device name as prefix."""
    device = create_device(hass, "selected_device")
    entry = create_time_entry({"device_id": device.id})

    await setup_with_mock_config(hass, entry)

    entity_id = get_sensor_entity_id(hass)
    assert entity_id == "sensor.selected_device_test_day"
    state = hass.states.get(entity_id)
    assert state
    assert state.attributes["friendly_name"] == "selected_device test_day"
    await unload_with_mock_config(hass, entry)


async def test_time_meter_without_device(hass: HomeAssistant) -> None:
    """Test a time meter without a selected device is not linked."""
    entry = create_time_entry()

    await setup_with_mock_config(hass, entry)

    assert get_sensor_device_id(hass) is None
    await unload_with_mock_config(hass, entry)


async def test_removed_device_is_ignored(hass: HomeAssistant) -> None:
    """Test setup still works when the selected device no longer exists."""
    entry = create_time_entry({"device_id": "non_existing_device"})

    await setup_with_mock_config(hass, entry)

    assert get_sensor_device_id(hass) is None
    await unload_with_mock_config(hass, entry)


async def test_changing_device_relinks_sensors(hass: HomeAssistant) -> None:
    """Test changing the device in the options relinks the sensors."""
    first_device = create_device(hass, "first_device")
    second_device = create_device(hass, "second_device")
    entry = create_time_entry({"device_id": first_device.id})
    await setup_with_mock_config(hass, entry)
    assert get_sensor_device_id(hass) == first_device.id

    hass.config_entries.async_update_entry(
        entry, options={**entry.options, "device_id": second_device.id}
    )
    await hass.async_block_till_done()
    assert get_sensor_device_id(hass) == second_device.id

    options = dict(entry.options)
    del options["device_id"]
    hass.config_entries.async_update_entry(entry, options=options)
    await hass.async_block_till_done()
    assert get_sensor_device_id(hass) is None

    await unload_with_mock_config(hass, entry)


async def test_clearing_device_unlinks_source_meter(hass: HomeAssistant) -> None:
    """Test clearing the device unlinks a source meter, despite its source device."""
    source_device = create_device(hass, "source_device")
    register_source_entity(hass, source_device)
    entry = create_source_entry({"device_id": source_device.id})
    await setup_with_mock_config(hass, entry)
    assert get_sensor_device_id(hass) == source_device.id

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "edit_main"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "when_days": ["0", "1", "2", "3", "4", "5", "6"],
            "when_from": "00:00:00",
            "when_till": "00:00:00",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    assert "device_id" not in entry.options
    assert get_sensor_device_id(hass) is None
    await unload_with_mock_config(hass, entry)
