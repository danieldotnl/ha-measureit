"""Adds config flow for Blueprint."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import uuid

import voluptuous as vol
from homeassistant.const import (
    CONF_NAME,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_VALUE_TEMPLATE,
    CONF_DEVICE_CLASS,
    CONF_UNIQUE_ID,
)

from homeassistant.components.sensor import (
    CONF_STATE_CLASS,
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.helpers import selector

from homeassistant.helpers.schema_config_entry_flow import (
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
    SchemaFlowMenuStep,
    SchemaCommonFlowHandler,
)

from .const import (
    CONF_CONDITION,
    CONF_PERIODS,
    CONF_SOURCE,
    CONF_TW_DAYS,
    CONF_TW_FROM,
    CONF_TW_TILL,
    DOMAIN,
)

PERIOD_OPTIONS = [
    # selector.SelectOptionDict(value="none", label="none (no reset)"),
    selector.SelectOptionDict(value="5m", label="5m"),
    selector.SelectOptionDict(value="hour", label="hour"),
    selector.SelectOptionDict(value="day", label="day"),
    selector.SelectOptionDict(value="week", label="week"),
    selector.SelectOptionDict(value="month", label="month"),
    selector.SelectOptionDict(value="year", label="year"),
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


async def validate_sensor_setup(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Validate sensor input."""
    user_input[CONF_UNIQUE_ID] = str(uuid.uuid1())

    # Standard behavior is to merge the result with the options.
    # In this case, we want to add a sub-item so we update the options directly.
    sensors: list[dict[str, Any]] = handler.options.setdefault(SENSOR_DOMAIN, [])
    sensors.append(user_input)
    return {}


async def validate_main_config(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Validate main config."""
    return user_input


MAIN_CONFIG = {
    vol.Required(CONF_NAME): selector.TextSelector(),
}

SENSOR_CONFIG = {
    vol.Optional(CONF_PERIODS): selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=PERIOD_OPTIONS,
            multiple=True,
            mode=selector.SelectSelectorMode.LIST,
        )
    )
}

WHEN_CONFIG = {
    vol.Optional(CONF_CONDITION): selector.TemplateSelector(),
    vol.Optional(CONF_TW_DAYS, default=DEFAULT_DAYS): selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=DAY_OPTIONS,
            multiple=True,
            mode=selector.SelectSelectorMode.LIST,
        ),
    ),
    vol.Required(CONF_TW_FROM): selector.TimeSelector(),
    vol.Required(CONF_TW_TILL): selector.TimeSelector(),
}

SENSORS_CONFIG = {
    vol.Optional(CONF_PERIODS): selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=PERIOD_OPTIONS,
            multiple=True,
            custom_value=True,
            mode=selector.SelectSelectorMode.LIST,
        )
    ),
    vol.Optional(CONF_UNIT_OF_MEASUREMENT): selector.TextSelector(),
    vol.Optional(CONF_VALUE_TEMPLATE): selector.TemplateSelector(),
    vol.Optional(CONF_DEVICE_CLASS): selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[cls.value for cls in SensorDeviceClass],
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    ),
    vol.Optional(CONF_STATE_CLASS): selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[cls.value for cls in SensorStateClass],
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    ),
}


DATA_SCHEMA_TIME = vol.Schema(MAIN_CONFIG)
DATA_SCHEMA_SOURCE = vol.Schema(
    {
        **MAIN_CONFIG,
        vol.Required(CONF_SOURCE): selector.EntitySelector(),
    }
)
DATA_SCHEMA_WHEN = vol.Schema(WHEN_CONFIG)
DATA_SCHEMA_EDIT_SENSOR = vol.Schema(SENSOR_CONFIG)
DATA_SCHEMA_SENSORS = vol.Schema(SENSORS_CONFIG)

CONFIG_FLOW = {
    "user": SchemaFlowMenuStep(["time", "source"]),
    "time": SchemaFlowFormStep(
        schema=DATA_SCHEMA_TIME,
        next_step="when",
        validate_user_input=validate_main_config,
    ),
    "source": SchemaFlowFormStep(
        schema=DATA_SCHEMA_SOURCE,
        next_step="when",
        # validate_user_input=validate_rest_setup,
    ),
    "when": SchemaFlowFormStep(
        schema=DATA_SCHEMA_WHEN,
        next_step="sensors",
    ),
    "sensors": SchemaFlowFormStep(
        schema=DATA_SCHEMA_SENSORS,
        validate_user_input=validate_sensor_setup,
    ),
}


class MeasureItFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config flow for Scrape."""

    config_flow = CONFIG_FLOW
    # options_flow = OPTIONS_FLOW

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        return options[CONF_NAME]
