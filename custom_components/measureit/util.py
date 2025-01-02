"""Utilities for MeasureIt."""

import logging
from collections.abc import Callable
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.template import Template

_LOGGER: logging.Logger = logging.getLogger(__name__)


def create_renderer(
    hass: HomeAssistant, value_template: str, round_digits_when_none: int | None = None
) -> Callable[[Any], Any]:
    """Create a renderer based on variable_template value."""
    if value_template is None:
        if round_digits_when_none is not None:
            return lambda value: round(value, round_digits_when_none)
        return lambda value: value

    parsed_value_template = Template(value_template, hass)

    def _render(value: Any) -> Any:
        try:
            return parsed_value_template.async_render(
                {"value": value}, parse_result=False
            )
        except TemplateError:
            _LOGGER.exception("Error parsing value")
            return value

    return _render
