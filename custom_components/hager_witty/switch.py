"""Schalter-Plattform: Verfügbarkeit und Fallback-Verzögerung der Witty."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .data import WittyConfigEntry
from .entity import WittyEntity

PARALLEL_UPDATES = 1

SWITCH_DESCRIPTIONS: tuple[SwitchEntityDescription, ...] = (
    # 0x3020: 0 = Ladestation gesperrt (HMI rot), 1 = verfügbar
    SwitchEntityDescription(key="evcs_available"),
    # 0x3021: Wert, den die Wallbox bei Verbindungsverlust übernimmt
    SwitchEntityDescription(key="evcs_available_fallback", entity_category=EntityCategory.CONFIG),
    # 0x3026: 0 = Fallback sofort, 1 = Fallback nach 30 s Verzögerung
    SwitchEntityDescription(key="fallback_delay", entity_category=EntityCategory.CONFIG),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WittyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Richte die Schalter-Plattform ein."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(WittySwitch(coordinator, description) for description in SWITCH_DESCRIPTIONS)


class WittySwitch(WittyEntity, SwitchEntity):
    """Ein 0/1-Register der Wallbox."""

    entity_description: SwitchEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Gibt den aktuellen Zustand zurück (Registerwert 1 = an)."""
        raw = self.coordinator.data.get(self.entity_description.key)
        return None if raw is None else raw == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Schalte an (Register = 1)."""
        await self.coordinator.async_write_value(self.entity_description.key, 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Schalte aus (Register = 0)."""
        await self.coordinator.async_write_value(self.entity_description.key, 0)
