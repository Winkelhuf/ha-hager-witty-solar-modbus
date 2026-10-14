"""
Runtime data types for the Hager Witty Modbus integration.

Access pattern: entry.runtime_data.client / entry.runtime_data.coordinator
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .client import WittyClient
    from .coordinator import WittyCoordinator


type WittyConfigEntry = ConfigEntry["WittyData"]


@dataclass
class WittyData:
    """Runtime data stored on the config entry after a successful setup."""

    client: "WittyClient"
    coordinator: "WittyCoordinator"
