"""Constants for MeasureIt."""
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

NAME = "MeasureIt"
DOMAIN = "measureit"
VERSION = "0.0.1"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"

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
CONF_SENSORS = "sensors"
CONF_STATE_CLASS = "state_class"
CONF_TW_DAYS = "when_days"
CONF_TW_FROM = "when_from"
CONF_TW_TILL = "when_till"

CONF_INDEX = "index"
