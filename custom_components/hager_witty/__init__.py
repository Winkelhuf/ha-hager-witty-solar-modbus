"""Die Hager Witty Modbus Integration."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .client import WittyClient
from .const import CONF_UNIT_ID, DEFAULT_PORT, DEFAULT_UNIT_ID
from .coordinator import WittyCoordinator
from .data import WittyConfigEntry, WittyData

# Hier definieren wir, welche Plattformdateien Home Assistant laden soll
PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: WittyConfigEntry) -> bool:
    """Wird aufgerufen, wenn die Integration in Home Assistant geladen wird."""
    client = WittyClient(
        entry.data[CONF_HOST],
        entry.data.get(CONF_PORT, DEFAULT_PORT),
        entry.data.get(CONF_UNIT_ID, DEFAULT_UNIT_ID),
    )
    coordinator = WittyCoordinator(hass, entry, client)

    # Die Witty erlaubt nur EINE TCP-Verbindung: beim Entladen/Neuladen (und wenn die
    # Einrichtung fehlschlägt) muss sie sauber geschlossen werden.
    entry.async_on_unload(client.async_close)

    # Erste Abfrage: bei Verbindungsproblemen wiederholt Home Assistant die Einrichtung.
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = WittyData(client=client, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Änderungen an den Optionen (Abfrageintervall) laden die Integration neu.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: WittyConfigEntry) -> bool:
    """Wird aufgerufen, wenn die Integration entfernt oder neu geladen wird."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: WittyConfigEntry) -> None:
    """Integration nach geänderten Optionen neu laden."""
    await hass.config_entries.async_reload(entry.entry_id)
