"""Support for Hager Witty Solar switches and coils."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    COIL_STATION_AVAILABLE,
    COIL_SWITCH_3_TO_1,
    COIL_LOCK_CABLE,
    COIL_ENABLE_RFID_AUTH,
)
from .coordinator.base import WittySolarDataUpdateCoordinator
from .entity.base import WittySolarEntity

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Witty Solar switch entities."""
    coordinator: WittySolarDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    switches = [
        WittySolarSwitch(coordinator, "Station Available", "coil_station_available", COIL_STATION_AVAILABLE),
        WittySolarSwitch(coordinator, "Switch 3 to 1 Phase", "coil_switch_3_to_1", COIL_SWITCH_3_TO_1),
        WittySolarSwitch(coordinator, "Lock Cable", "coil_lock_cable", COIL_LOCK_CABLE),
        WittySolarSwitch(coordinator, "RFID Authentication", "coil_enable_rfid_auth", COIL_ENABLE_RFID_AUTH),
    ]

    async_add_entities(switches)

class WittySolarSwitch(WittySolarEntity, SwitchEntity):
    """Representation of a Witty Solar Switch/Coil."""

    def __init__(self, coordinator: WittySolarDataUpdateCoordinator, name: str, key: str, coil_address: int) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, name, key)
        self._key = key
        self._coil_address = coil_address

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return bool(self.coordinator.data.get(self._key, False))

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self.coordinator.async_write_coil(self._coil_address, True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self.coordinator.async_write_coil(self._coil_address, False)