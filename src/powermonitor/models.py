"""Data models for powermonitor - matches Rust implementation exactly."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class PowerReading:
    """Real-time power reading snapshot - matches Rust PowerReading struct exactly.

    All 12 fields correspond to the Rust implementation in powermonitor-core/src/models.rs
    """

    # Timestamp
    timestamp: datetime

    # Power metrics
    watts_actual: (
        float  # Actual power flow: positive = charging, negative = discharging (W)
    )
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
    """Raw adapter details from ioreg - matches Rust AdapterDetail struct."""

    watts: int | None  # Negotiated power (W)
    name: str | None  # Charger name
    description: str | None  # Description
    manufacturer: str | None  # Manufacturer
    voltage: int | None  # Charger voltage (mV)
    current: int | None  # Charger current (mA)


class PowerCollectorError(Exception):
    """Base exception for power collection errors."""

    pass


class CommandFailedError(PowerCollectorError):
    """ioreg command execution failed."""

    pass


class ParseError(PowerCollectorError):
    """Plist/data parsing failed."""

    pass


class MissingFieldError(PowerCollectorError):
    """Required field is missing from power data."""

    def __init__(self, field_name: str):
        super().__init__(f"Missing required field: {field_name}")
        self.field_name = field_name


class IOKitError(PowerCollectorError):
    """IOKit/SMC API error."""

    pass
