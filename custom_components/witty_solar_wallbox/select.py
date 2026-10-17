"""Select-Plattform für die Witty-Solar-Wallbox: LED-Modus (Register 0x0052).

Das Register 0x0052 heißt in der Spec "Boost/Solar mode", ändert laut §3.3.23
aber ausschließlich das Verhalten der HMI-LED (Farbmuster in allen CP-Zuständen):
0 = Witty Start (Standard), 1 = Boost, 2 = Solar.
Es verändert NICHT die Ladeleistung - dafür gibt es den Boost-Schalter (Maximalstrom).
"""
from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import WittySolarEntity
from .registers import LED_MODE_MAP, LED_MODE_MAP_REVERSE

LED_MODE_SELECT_DESCRIPTION = SelectEntityDescription(
    key="led_mode_select",
    translation_key="led_mode_select",
    icon="mdi:weather-sunny",
    options=list(LED_MODE_MAP.values()),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Richte die Select-Plattform ein."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities([WittySolarLedModeSelect(coordinator, LED_MODE_SELECT_DESCRIPTION, entry.entry_id)])


class WittySolarLedModeSelect(WittySolarEntity, SelectEntity):
    """Wählt den LED-Modus der HMI (Register 0x0052)."""

    @property
    def current_option(self) -> str | None:
        """Aktuell aktiver Modus."""
        raw = self.coordinator.data.get("led_mode")
        return None if raw is None else LED_MODE_MAP.get(int(raw))

    async def async_select_option(self, option: str) -> None:
        """Schreibt den gewählten Modus auf die Wallbox."""
        await self.coordinator.async_write_led_mode(LED_MODE_MAP_REVERSE[option])
