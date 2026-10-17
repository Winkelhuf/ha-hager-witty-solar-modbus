"""Constants for the Witty Solar Wallbox (generic Hager EVCS/B1280) integration."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "witty_solar_wallbox"
VERSION = "0.1.0"

DEFAULT_PORT = 502

# Die Spec (EVCS_Modbus v0.28) nennt keine Unit-ID. Wir verwenden standardmäßig 1
# und machen sie im Config Flow einstellbar.
UNIT_ID = 1  # Standardwert, in der Konfiguration änderbar (Option "slave")

CONF_HOST = "host"
CONF_PORT = "port"

# Fallback, falls das Hardware-Limit (noch) nicht gelesen werden konnte.
DEFAULT_MAX_CURRENT_A = 32
