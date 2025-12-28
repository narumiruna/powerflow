"""IORegCollector - subprocess-based power collector using ioreg command."""

import plistlib
import subprocess
from datetime import UTC
from datetime import datetime

from ..models import CommandFailedError
from ..models import MissingFieldError
from ..models import ParseError
from ..models import PowerReading


class IORegCollector:
    """Collect power data by parsing ioreg command output.

    This is the fallback collector that doesn't require IOKit permissions.
    Executes `ioreg -rw0 -c AppleSmartBattery -a` and parses the plist output.

    # IORegCollector implementation details
    """

    def collect(self) -> PowerReading:
        """Collect current power reading from ioreg.

        Returns:
            PowerReading with current power data

        Raises:
            CommandFailedError: If ioreg execution fails
            ParseError: If plist parsing fails
            MissingFieldError: If required fields are missing
        """
        # Execute ioreg command
        try:
            result = subprocess.run(
                ["ioreg", "-rw0", "-c", "AppleSmartBattery", "-a"],
                capture_output=True,
                text=False,  # Get bytes for plist parsing
                check=True,
                timeout=10,
            )
        except subprocess.CalledProcessError as e:
            raise CommandFailedError(f"ioreg command failed: {e}") from e
        except subprocess.TimeoutExpired as e:
            raise CommandFailedError(f"ioreg command timed out: {e}") from e
        except FileNotFoundError as e:
            raise CommandFailedError("ioreg command not found (not macOS?)") from e

        # Parse plist output
        try:
            plist_data = plistlib.loads(result.stdout)
        except Exception as e:
            raise ParseError(f"Failed to parse plist data: {e}") from e

        # ioreg returns an array with one battery dictionary
        if not isinstance(plist_data, list) or len(plist_data) == 0:
            raise ParseError("Unexpected plist structure: expected array with battery data")

        battery = plist_data[0]

        # Parse battery data into PowerReading
        return self._parse_battery_data(battery)

    def _parse_battery_data(self, battery: dict) -> PowerReading:
        """Parse battery dictionary into PowerReading.

        Args:
            battery: Dictionary from ioreg plist output

        Returns:
            PowerReading with parsed data

        Raises:
            MissingFieldError: If required fields are missing
        """
        # Extract required fields with error handling
        try:
            voltage_mv = battery["Voltage"]  # mV
            amperage_ma = battery["Amperage"]  # mA (negative = discharging)
        except KeyError as e:
            raise MissingFieldError(str(e.args[0])) from e

        # Convert units: mV → V, mA → A
        voltage = voltage_mv / 1000.0
        amperage = amperage_ma / 1000.0

        # Calculate actual watts: V × A
        watts_actual = PowerReading.calculate_watts(voltage, amperage)

        # Battery capacity (prefer raw values over percentage-based)
        current_capacity = battery.get("AppleRawCurrentCapacity", battery.get("CurrentCapacity", 0))
        max_capacity = battery.get("AppleRawMaxCapacity", battery.get("MaxCapacity", 1))

        # Battery percentage
        battery_percent = round((current_capacity / max_capacity) * 100) if max_capacity > 0 else 0

        # Charging status
        is_charging = battery.get("IsCharging", False)
        external_connected = battery.get("ExternalConnected", False)

        # Adapter details (negotiated power and charger info)
        watts_negotiated = 0
        charger_name = None
        charger_manufacturer = None

        adapter_details = battery.get("AppleRawAdapterDetails")
        if adapter_details and isinstance(adapter_details, list) and len(adapter_details) > 0:
            adapter = adapter_details[0]
            watts_negotiated = adapter.get("Watts", 0)
            charger_name = adapter.get("Name")
            charger_manufacturer = adapter.get("Manufacturer")

        return PowerReading(
            timestamp=datetime.now(tz=UTC),
            watts_actual=watts_actual,
            watts_negotiated=watts_negotiated,
            voltage=voltage,
            amperage=amperage,
            current_capacity=current_capacity,
            max_capacity=max_capacity,
            battery_percent=battery_percent,
            is_charging=is_charging,
            external_connected=external_connected,
            charger_name=charger_name,
            charger_manufacturer=charger_manufacturer,
        )
