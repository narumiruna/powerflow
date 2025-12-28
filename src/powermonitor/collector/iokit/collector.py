"""IOKit-based power collector using SMC sensors."""

from dataclasses import dataclass

from loguru import logger

from ...models import PowerReading
from ..base import PowerCollector
from ..ioreg import IORegCollector
from .connection import SMCConnection
from .connection import SMCError

# SMC sensor keys for power monitoring
SMC_SENSORS = {
    "PPBR": "Battery power rate (W) - positive when discharging",
    "PDTR": "Power delivery/input rate (W)",
    "PSTR": "System total power consumption (W)",
    "PHPC": "Heatpipe/cooling power (W)",
    "PDBR": "Display brightness power (W)",
    "TB0T": "Battery temperature (°C)",
    "CHCC": "Charging status (0 = not charging)",
}


@dataclass
class SMCPowerData:
    """SMC power sensor readings."""

    battery_power: float | None = None  # PPBR
    power_input: float | None = None  # PDTR (most accurate)
    system_power: float | None = None  # PSTR
    heatpipe_power: float | None = None  # PHPC
    display_power: float | None = None  # PDBR
    battery_temp: float | None = None  # TB0T
    charging_status: float | None = None  # CHCC


class IOKitCollector(PowerCollector):
    """Power collector using IOKit/SMC sensors.

    This collector provides more accurate power readings by directly accessing
    macOS SMC sensors via IOKit. Falls back to IORegCollector if SMC access fails.

    SMC sensors used:
    - PDTR: Power delivery/input rate (W) - Most accurate for watts_actual
    - PPBR: Battery power rate (W)
    - PSTR: System total power consumption (W)
    - PHPC: Heatpipe/cooling power (W)
    - PDBR: Display brightness power (W)
    - TB0T: Battery temperature (°C)
    - CHCC: Charging status
    """

    def __init__(self, verbose: bool = False):
        """Initialize IOKit collector.

        Args:
            verbose: If True, print debug info about SMC sensors
        """
        self.verbose = verbose
        self.fallback_collector = IORegCollector()

    def collect(self) -> PowerReading:
        """Collect power data from SMC sensors and IORegistry.

        Returns:
            PowerReading with enhanced data from SMC sensors

        Raises:
            Exception: If both SMC and fallback collection fail
        """
        try:
            return self._collect_with_smc()
        except (SMCError, Exception) as e:
            if self.verbose:
                logger.warning(f"SMC access failed: {e}")
                logger.info("Falling back to IORegCollector...")
            return self.fallback_collector.collect()

    def _collect_with_smc(self) -> PowerReading:
        """Collect power data using SMC sensors.

        Returns:
            PowerReading enhanced with SMC sensor data
        """
        # Read SMC sensors
        smc_data = self._read_smc_sensors()

        # Get base battery info from IORegistry (via ioreg subprocess)
        # In production, this could use direct IORegistry API calls
        reading = self.fallback_collector.collect()

        # Enhance reading with SMC data
        # PDTR (Power Delivery/Input Rate) is most accurate for watts_actual
        if smc_data.power_input is not None:
            reading.watts_actual = smc_data.power_input

        # Debug output if verbose
        if self.verbose:
            logger.debug("SMC Sensor Data:")
            logger.debug(f"  PPBR (Battery Power): {smc_data.battery_power}W")
            logger.debug(f"  PDTR (Power Input): {smc_data.power_input}W")
            logger.debug(f"  PSTR (System Power): {smc_data.system_power}W")
            logger.debug(f"  PHPC (Heatpipe): {smc_data.heatpipe_power}W")
            logger.debug(f"  PDBR (Display): {smc_data.display_power}W")
            logger.debug(f"  TB0T (Battery Temp): {smc_data.battery_temp}°C")
            logger.debug(f"  CHCC (Charging): {smc_data.charging_status}")
            logger.debug(f"Using PDTR for watts_actual: {reading.watts_actual}W")

        return reading

    def _read_smc_sensors(self) -> SMCPowerData:
        """Read all SMC power sensors.

        Returns:
            SMCPowerData with sensor readings (None for unavailable sensors)

        Raises:
            SMCError: If SMC connection fails
        """
        data = SMCPowerData()

        with SMCConnection() as smc:
            # Try to read each sensor, but don't fail if some are missing
            for key in ["PPBR", "PDTR", "PSTR", "PHPC", "PDBR", "TB0T", "CHCC"]:
                try:
                    value = smc.read_key(key)

                    if key == "PPBR":
                        data.battery_power = value
                    elif key == "PDTR":
                        data.power_input = value
                    elif key == "PSTR":
                        data.system_power = value
                    elif key == "PHPC":
                        data.heatpipe_power = value
                    elif key == "PDBR":
                        data.display_power = value
                    elif key == "TB0T":
                        data.battery_temp = value
                    elif key == "CHCC":
                        data.charging_status = value

                except SMCError:
                    # Sensor not available on this Mac model
                    pass

        return data
