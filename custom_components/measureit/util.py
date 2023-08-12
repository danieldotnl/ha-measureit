"""Utilities for MeasureIt."""
import logging
from decimal import Decimal
from typing import Union

from homeassistant.exceptions import TemplateError
from homeassistant.helpers.template import Template

NumberType = Union[float, Decimal, int]  # noqa: UP007

_LOGGER: logging.Logger = logging.getLogger(__name__)


def create_renderer(hass, value_template):
    """Create a renderer based on variable_template value."""
    if value_template is None:
        return lambda value: value

    value_template = Template(value_template, hass)

    def _render(value):
        try:
            return value_template.async_render({"value": value}, parse_result=False)
        except TemplateError:
            _LOGGER.exception("Error parsing value")
            return value

    return _render
