"""Support for Hager Witty Solar switches and coils."""
from __future__ import annotations

import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, COIL_STATION_AVAILABLE, COIL_SWITCH_3_TO_1, COIL_ENABLE_RFID_AUTH, COIL_EV41_COMPLIANCE

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: config_entries.ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Witty Solar switch entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    switches = [
        WittySwitch(coordinator, "Station Available", COIL_STATION_AVAILABLE),
        WittySwitch(coordinator, "Switch 3 to 1 Phase", COIL_SWITCH_3_TO_1),
        WittySwitch(coordinator, "RFID Authentication", COIL_ENABLE_RFID_AUTH),
        WittySwitch(coordinator, "EV41 Compliance", COIL_EV41_COMPLIANCE),
    ]
    
    async_add_entities(switches)

class WittySwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Witty Solar Switch/Coil."""

    def __init__(self, coordinator, name, coil_address):
        """Initialize the switch."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_name = f"Witty Solar {name}"
        self._coil_address = coil_address
        self._attr_unique_id = f"witty_solar_coil_{coil_address}"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return bool(self.coordinator.data.get(f"coil_{self._coil_address}", False))

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        client = self.coordinator.modbus_client
        await client.write_coil(self._coil_address, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        client = self.coordinator.modbus_client
        await client.write_coil(self._coil_address, False)
        await self.coordinator.async_request_refresh()