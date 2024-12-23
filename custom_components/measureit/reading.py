"""Data class for reading data."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ReadingData:
    """Class containing data for a specific reading."""

    reading_datetime: datetime = None
    template_active: bool = None
    timewindow_active: bool = None
    value: float = None
