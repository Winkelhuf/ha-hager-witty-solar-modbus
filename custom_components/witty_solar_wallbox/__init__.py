"""Die Hager Witty Solar Wallbox Integration (generisches EVCS/B1280-Board)."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SLAVE, Platform
from homeassistant.core import HomeAssistant

from .const import UNIT_ID
from .coordinator import WittySolarCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.SELECT,
]


@dataclass
class WittySolarRuntimeData:
    """Runtime-Daten der Config Entry."""

    coordinator: WittySolarCoordinator


WittySolarConfigEntry = ConfigEntry[WittySolarRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: WittySolarConfigEntry) -> bool:
    """Richte die Integration für einen Config Entry ein."""
    coordinator = WittySolarCoordinator(
        hass, entry.data[CONF_HOST], entry.data[CONF_PORT], entry.data.get(CONF_SLAVE, UNIT_ID)
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = WittySolarRuntimeData(coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: WittySolarConfigEntry) -> bool:
    """Entlade den Config Entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry.runtime_data.coordinator.client.close()
    return unload_ok
