"""Data models for powermonitor."""

from dataclasses import dataclass
from datetime import datetime

from peewee import BooleanField
from peewee import DateTimeField
from peewee import FloatField
from peewee import IntegerField
from peewee import Model
from peewee import SqliteDatabase
from peewee import TextField

db = SqliteDatabase(None)  # Delayed initialization


@dataclass
class PowerReading:
    """Real-time power reading snapshot."""

    # Timestamp
    timestamp: datetime

    # Power metrics
    watts_actual: float  # Actual power flow: positive = charging, negative = discharging (W)
    watts_negotiated: int  # PD negotiated maximum power (W)

    # Electrical details
    voltage: float  # Voltage (V)
    amperage: float  # Current (A)

    # Battery state
    current_capacity: int  # Current battery capacity (mAh)
    max_capacity: int  # Maximum battery capacity (mAh)
    battery_percent: int  # Battery percentage (0-100)

    # Status
    is_charging: bool  # Is battery currently charging
    external_connected: bool  # Is external power connected
    charger_name: str | None  # Charger/adapter name
    charger_manufacturer: str | None  # Charger manufacturer

    @staticmethod
    def calculate_watts(voltage: float, amperage: float) -> float:
        """Calculate actual wattage from voltage and amperage.

        Args:
            voltage: Voltage in V
            amperage: Amperage in A

        Returns:
            Power in W
        """
        return voltage * amperage


@dataclass
class AdapterDetail:
    """Raw adapter details from ioreg."""

    watts: int | None  # Negotiated power (W)
    name: str | None  # Charger name
    description: str | None  # Description
    manufacturer: str | None  # Manufacturer
    voltage: int | None  # Charger voltage (mV)
    current: int | None  # Charger current (mA)


class PowerCollectorError(Exception):
    """Base exception for power collection errors."""


class CommandFailedError(PowerCollectorError):
    """ioreg command execution failed."""


class ParseError(PowerCollectorError):
    """Plist/data parsing failed."""


class MissingFieldError(PowerCollectorError):
    """Required field is missing from power data."""

    def __init__(self, field_name: str):
        super().__init__(f"Missing required field: {field_name}")
        self.field_name = field_name


class IOKitError(PowerCollectorError):
    """IOKit/SMC API error."""


class PowerReadingModel(Model):
    """Peewee ORM model for power_readings table.

    Note: This is a base model definition. The Database class creates
    per-instance models bound to specific database connections.
    """

    timestamp = DateTimeField()
    watts_actual = FloatField()
    watts_negotiated = IntegerField()
    voltage = FloatField()
    amperage = FloatField()
    current_capacity = IntegerField()
    max_capacity = IntegerField()
    battery_percent = IntegerField()
    is_charging = BooleanField()
    external_connected = BooleanField()
    charger_name = TextField(null=True)
    charger_manufacturer = TextField(null=True)

    class Meta:
        database = db
        table_name = "power_readings"
