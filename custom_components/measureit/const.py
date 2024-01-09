"""Constants for MeasureIt."""
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

NAME = "MeasureIt"
DOMAIN = "measureit"
DOMAIN_DATA = "measureit_data"
VERSION = "0.0.1"
COORDINATOR = "coordinator"
STORE = "store"
SOURCE_ENTITY_ID = "source_entity_id"

# Icons
ICON = "mdi:measure"

# Configuration and options
CONF_SOURCE = "source"
CONF_ENABLED = "enabled"
CONF_METER_TYPE = "meter_type"
CONF_SOURCE = "source_entity"
CONF_CONDITION = "condition"
CONF_TARGET = "target_sensor"
CONF_METERS = "meters"
CONF_PERIODS = "periods"
CONF_CRON = "cron"
CONF_PERIOD = "period"
CONF_SENSOR = "sensor"
CONF_STATE_CLASS = "state_class"
CONF_TW_DAYS = "when_days"
CONF_TW_FROM = "when_from"
CONF_TW_TILL = "when_till"
CONF_CONFIG_NAME = "config_name"
CONF_SENSOR_NAME = "sensor_name"
CONF_INDEX = "index"

METER_TYPE_TIME = "time"
METER_TYPE_SOURCE = "source"

# Attributes
ATTR_PREV = "prev_period"
ATTR_NEXT_RESET = "next_reset"
ATTR_STATUS = "status"

PREDEFINED_PERIODS = {
    "5m": "*/5 * * * *",
    "hour": "0 * * * *",
    "day": "0 0 * * *",
    "week": "0 0 * * 1",
    "month": "0 0 1 * *",
    "year": "0 0 1 1 *",
    "forever": "none",
}
