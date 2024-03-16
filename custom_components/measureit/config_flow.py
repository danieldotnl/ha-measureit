"""Adds config flow for MeasureIt."""

# Handling multiple sensors was inspired by the config_flow for the HA scrape sensor.

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.components.sensor import CONF_STATE_CLASS
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (CONF_DEVICE_CLASS, CONF_UNIQUE_ID,
                                 CONF_UNIT_OF_MEASUREMENT, CONF_VALUE_TEMPLATE)
from homeassistant.core import async_get_hass
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaCommonFlowHandler, SchemaConfigFlowHandler, SchemaFlowError,
    SchemaFlowFormStep, SchemaFlowMenuStep)
from homeassistant.helpers.template import Template

from .const import (CONF_CONDITION, CONF_CONFIG_NAME, CONF_COUNTER_TEMPLATE,
                    CONF_CRON, CONF_INDEX, CONF_METER_TYPE, CONF_PERIOD,
                    CONF_PERIODS, CONF_SENSOR_NAME, CONF_SOURCE, CONF_TW_DAYS,
                    CONF_TW_FROM, CONF_TW_TILL, DOMAIN, LOGGER,
                    PREDEFINED_PERIODS, MeterType)

PERIOD_OPTIONS = [
    # selector.SelectOptionDict(value="none", label="none (no reset)"),
    selector.SelectOptionDict(value="hour", label="hour"),
    selector.SelectOptionDict(value="day", label="day"),
    selector.SelectOptionDict(value="week", label="week"),
    selector.SelectOptionDict(value="month", label="month"),
    selector.SelectOptionDict(value="year", label="year"),
    selector.SelectOptionDict(value="noreset", label="noreset"),
    selector.SelectOptionDict(value="session", label="session"),
]

DAY_OPTIONS = [
    selector.SelectOptionDict(value="0", label="monday"),
    selector.SelectOptionDict(value="1", label="tuesday"),
    selector.SelectOptionDict(value="2", label="wednesday"),
    selector.SelectOptionDict(value="3", label="thursday"),
    selector.SelectOptionDict(value="4", label="friday"),
    selector.SelectOptionDict(value="5", label="saturday"),
    selector.SelectOptionDict(value="6", label="sunday"),
]
DEFAULT_DAYS = ["0", "1", "2", "3", "4", "5", "6"]


def make_unique_name(name, existing_names):
    """Create a unique name with a suffix in case of duplicates."""
    if name not in existing_names:
        return name

    # Find a unique suffix
    suffix = 1
    while f"{name}_{suffix}" in existing_names:
        suffix += 1

    return f"{name}_{suffix}"


async def validate_sensor_setup(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Validate sensor input."""

    # Standard behavior is to merge the result with the options.
    # In this case, we want to add a sub-item so we update the options directly.
    sensors: list[dict[str, Any]] = handler.options.setdefault(SENSOR_DOMAIN, [])
    for period in user_input[CONF_PERIODS]:
        sensor = dict(user_input)
        sensor[CONF_UNIQUE_ID] = str(uuid.uuid1())

        sensor[CONF_SENSOR_NAME] = make_unique_name(
            period, [item.get(CONF_SENSOR_NAME) for item in sensors]
        )
        sensor[CONF_CRON] = PREDEFINED_PERIODS[period]
        sensor[CONF_PERIOD] = period
        del sensor[CONF_PERIODS]
        sensors.append(sensor)

    return {}


async def validate_edit_main_config(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Validate edit main config."""
    return user_input


async def validate_time_config(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Validate time config."""
    user_input[CONF_METER_TYPE] = MeterType.TIME
    return user_input


async def validate_source_config(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Validate source config."""
    user_input[CONF_METER_TYPE] = MeterType.SOURCE
    return user_input


async def validate_count_config(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Validate source config."""
    user_input[CONF_METER_TYPE] = MeterType.COUNTER
    return user_input


async def validate_when(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Validate when config."""
    if len(user_input[CONF_TW_DAYS]) == 0:
        raise SchemaFlowError("tw_days_minimum")
    if user_input.get(CONF_CONDITION):
        template = Template(user_input[CONF_CONDITION])
        template.hass = async_get_hass()
        try:
            template.ensure_valid()
            template.async_render()
        except TemplateError as ex:
            raise SchemaFlowError("condition_invalid") from ex
    return user_input


async def get_select_sensor_schema(handler: SchemaCommonFlowHandler) -> vol.Schema:
    """Return schema for selecting a sensor."""
    return vol.Schema(
        {
            vol.Required(CONF_INDEX): vol.In(
                {
                    str(index): config[CONF_SENSOR_NAME]
                    for index, config in enumerate(handler.options[SENSOR_DOMAIN])
                },
            )
        }
    )


async def get_remove_sensor_schema(handler: SchemaCommonFlowHandler) -> vol.Schema:
    """Return schema for sensor removal."""
    return vol.Schema(
        {
            vol.Required(CONF_INDEX): cv.multi_select(
                {
                    str(index): config[CONF_SENSOR_NAME]
                    for index, config in enumerate(handler.options[SENSOR_DOMAIN])
                },
            )
        }
    )


async def validate_remove_sensor(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Validate remove sensor."""
    removed_indexes: set[str] = set(user_input[CONF_INDEX])

    # Standard behavior is to merge the result with the options.
    # In this case, we want to remove sub-items so we update the options directly.
    entity_registry = er.async_get(handler.parent_handler.hass)
    sensors: list[dict[str, Any]] = []
    sensor: dict[str, Any]
    for index, sensor in enumerate(handler.options[SENSOR_DOMAIN]):
        if str(index) not in removed_indexes:
            sensors.append(sensor)
        elif entity_id := entity_registry.async_get_entity_id(
            SENSOR_DOMAIN, DOMAIN, sensor[CONF_UNIQUE_ID]
        ):
            entity_registry.async_remove(entity_id)
    handler.options[SENSOR_DOMAIN] = sensors
    return {}


async def get_add_sensor_suggested_values(
    handler: SchemaCommonFlowHandler,
) -> dict[str, Any]:
    """Return suggested values for adding sensors."""
    suggested = {CONF_STATE_CLASS: SensorStateClass.TOTAL, CONF_PERIODS: ["day"]}
    if handler.options[CONF_METER_TYPE] == MeterType.TIME:
        suggested[CONF_DEVICE_CLASS] = SensorDeviceClass.DURATION
        suggested[CONF_UNIT_OF_MEASUREMENT] = "s"
        suggested[CONF_STATE_CLASS] = SensorStateClass.TOTAL_INCREASING
    elif handler.options[CONF_METER_TYPE] == MeterType.SOURCE:
        try:
            state = handler.parent_handler.hass.states.get(handler.options[CONF_SOURCE])
            suggested[CONF_DEVICE_CLASS] = state.attributes.get("device_class")
            suggested[CONF_UNIT_OF_MEASUREMENT] = state.attributes.get(
                "unit_of_measurement"
            )
        except Exception as ex:
            LOGGER.warning(
                "Couldn't retrieve properties from source entity in config_flow: %s", ex
            )
    elif handler.options[CONF_METER_TYPE] == MeterType.COUNTER:
        suggested[CONF_STATE_CLASS] = SensorStateClass.TOTAL_INCREASING
    return suggested


async def get_edit_sensor_suggested_values(
    handler: SchemaCommonFlowHandler,
) -> dict[str, Any]:
    """Return suggested values for sensor editing."""
    idx: int = handler.flow_state["_idx"]
    return handler.options[SENSOR_DOMAIN][idx]


async def validate_select_sensor(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Store sensor index in flow state."""
    handler.flow_state["_idx"] = int(user_input[CONF_INDEX])
    return {}


async def validate_sensor_edit(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Update edited sensor."""

    # Standard behavior is to merge the result with the options.
    # In this case, we want to add a sub-item so we update the options directly.
    idx: int = handler.flow_state["_idx"]
    if handler.options[SENSOR_DOMAIN][idx][CONF_UNIT_OF_MEASUREMENT] != user_input.get(CONF_UNIT_OF_MEASUREMENT):
        if handler.options[SENSOR_DOMAIN][idx][CONF_DEVICE_CLASS] and user_input.get(CONF_DEVICE_CLASS) is not None:
            raise SchemaFlowError("uom_with_device_class_update")
    handler.options[SENSOR_DOMAIN][idx].update(user_input)
    for key in DATA_SCHEMA_EDIT_SENSOR.schema:
        if isinstance(key, vol.Optional) and key not in user_input:
            # Key not present, delete keys old value (if present) too
            handler.options[SENSOR_DOMAIN][idx].pop(key, None)
    return {}


MAIN_CONFIG = {
    vol.Required(CONF_CONFIG_NAME): selector.TextSelector(),
}

SENSOR_CONFIG = {
    vol.Optional(CONF_VALUE_TEMPLATE): selector.TemplateSelector(),
    vol.Optional(CONF_UNIT_OF_MEASUREMENT): selector.TextSelector(),
    vol.Optional(CONF_DEVICE_CLASS): selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[cls.value for cls in SensorDeviceClass],
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    ),
    vol.Optional(CONF_STATE_CLASS): selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[SensorStateClass.TOTAL, SensorStateClass.TOTAL_INCREASING],
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    ),
}

WHEN_CONFIG = {
    vol.Optional(CONF_CONDITION): selector.TemplateSelector(),
    vol.Required(CONF_TW_DAYS, default=DEFAULT_DAYS): selector.SelectSelector(
        selector.SelectSelectorConfig(
            translation_key="day_selector",
            options=DAY_OPTIONS,
            multiple=True,
            mode=selector.SelectSelectorMode.LIST,
        ),
    ),
    vol.Required(CONF_TW_FROM): selector.TimeSelector(),
    vol.Required(CONF_TW_TILL): selector.TimeSelector(),
}

SENSORS_CONFIG = {
    vol.Required(CONF_PERIODS): selector.SelectSelector(
        selector.SelectSelectorConfig(
            translation_key="period_selector",
            options=PERIOD_OPTIONS,
            multiple=True,
            custom_value=False,
            mode=selector.SelectSelectorMode.LIST,
        )
    ),
    **SENSOR_CONFIG,
}

DATA_SCHEMA_TIME = vol.Schema(MAIN_CONFIG)
DATA_SCHEMA_SOURCE = vol.Schema(
    {
        **MAIN_CONFIG,
        vol.Required(CONF_SOURCE): selector.EntitySelector(),
    }
)
DATA_SCHEMA_COUNT = vol.Schema(
    {
        **MAIN_CONFIG,
        vol.Required(CONF_COUNTER_TEMPLATE): selector.TemplateSelector(),
    }
)
DATA_SCHEMA_WHEN = vol.Schema(WHEN_CONFIG)
DATA_SCHEMA_EDIT_SENSOR = vol.Schema(
    {vol.Required(CONF_SENSOR_NAME): selector.TextSelector(), **SENSOR_CONFIG}
)
DATA_SCHEMA_SENSORS = vol.Schema(SENSORS_CONFIG)

DATA_SCHEMA_EDIT_MAIN = vol.Schema(
    {
        **WHEN_CONFIG,
    }
)

DATA_SCHEMA_THANK_YOU = vol.Schema({})


CONFIG_FLOW = {
    "user": SchemaFlowMenuStep(["time", "source", "count"]),
    "time": SchemaFlowFormStep(
        schema=DATA_SCHEMA_TIME,
        next_step="when",
        validate_user_input=validate_time_config,
    ),
    "source": SchemaFlowFormStep(
        schema=DATA_SCHEMA_SOURCE,
        next_step="when",
        validate_user_input=validate_source_config,
    ),
    "count": SchemaFlowFormStep(
        schema=DATA_SCHEMA_COUNT,
        next_step="when",
        validate_user_input=validate_count_config,
    ),
    "when": SchemaFlowFormStep(
        schema=DATA_SCHEMA_WHEN,
        validate_user_input=validate_when,
        next_step="sensors",
    ),
    "sensors": SchemaFlowFormStep(
        schema=DATA_SCHEMA_SENSORS,
        validate_user_input=validate_sensor_setup,
        suggested_values=get_add_sensor_suggested_values,
        next_step="thank_you",
    ),
    "thank_you": SchemaFlowFormStep(
        DATA_SCHEMA_THANK_YOU,
    ),
}

OPTIONS_FLOW = {
    "init": SchemaFlowMenuStep(
        ["edit_main", "add_sensors", "select_edit_sensor", "remove_sensor"]
    ),
    "edit_main": SchemaFlowFormStep(
        DATA_SCHEMA_EDIT_MAIN,
        validate_user_input=validate_edit_main_config,
    ),
    "add_sensors": SchemaFlowFormStep(
        DATA_SCHEMA_SENSORS,
        suggested_values=get_add_sensor_suggested_values,
        validate_user_input=validate_sensor_setup,
        next_step="thank_you",
    ),
    "select_edit_sensor": SchemaFlowFormStep(
        get_select_sensor_schema,
        suggested_values=None,
        validate_user_input=validate_select_sensor,
        next_step="edit_sensor",
    ),
    "edit_sensor": SchemaFlowFormStep(
        DATA_SCHEMA_EDIT_SENSOR,
        suggested_values=get_edit_sensor_suggested_values,
        validate_user_input=validate_sensor_edit,
        next_step="thank_you",
    ),
    "remove_sensor": SchemaFlowFormStep(
        get_remove_sensor_schema,
        suggested_values=None,
        validate_user_input=validate_remove_sensor,
        next_step="thank_you",
    ),
    "thank_you": SchemaFlowFormStep(
        DATA_SCHEMA_THANK_YOU,
    ),
}


class MeasureItFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config flow for Scrape."""

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        return options[CONF_CONFIG_NAME]
