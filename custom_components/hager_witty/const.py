"""Constants for the Hager Witty Modbus integration."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "hager_witty"
VERSION = "0.1.0"

# Config entry data
CONF_UNIT_ID = "unit_id"

# Defaults (WittyPlus ModbusTCP developer's guide: port 502, unit identifier 1)
DEFAULT_NAME = "Witty"
DEFAULT_PORT = 502
DEFAULT_UNIT_ID = 1

# Options
DEFAULT_SCAN_INTERVAL = 5  # seconds
MIN_SCAN_INTERVAL = 2
MAX_SCAN_INTERVAL = 60

# Modbus
DEFAULT_TIMEOUT = 3.0  # seconds per request
# An "optional" register block that the wallbox rejected (e.g. the RFID registers
# while RFID authentication is switched off) is not requested again for this long.
OPTIONAL_BLOCK_RETRY_SECONDS = 300
