"""Select-Plattform: Phasenumschaltung und RFID-Rückmeldung der Witty."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .data import WittyConfigEntry
from .entity import WittyEntity
from .registers import PHASE_MODES, RFID_FEEDBACK

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class WittySelectEntityDescription(SelectEntityDescription):
    """Register-Wert -> Optionsschlüssel."""

    options_map: dict[int, str]


def _select(key: str, options_map: dict[int, str], **kwargs) -> WittySelectEntityDescription:
    return WittySelectEntityDescription(
        key=key,
        options=list(options_map.values()),
        options_map=options_map,
        **kwargs,
    )


SELECT_DESCRIPTIONS: tuple[WittySelectEntityDescription, ...] = (
    # Register 0x3022 "Switch3to1": 0 = 3 Phasen, 1 = nur 1 Phase
    _select("phase_mode", PHASE_MODES),
    _select("phase_mode_fallback", PHASE_MODES, entity_category=EntityCategory.CONFIG),
    # Register 0x400B: Ergebnis der Authentifizierung eines RFID-Tags
    _select(
        "rfid_feedback",
        RFID_FEEDBACK,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WittyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Richte die Select-Plattform ein."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(WittySelect(coordinator, description) for description in SELECT_DESCRIPTIONS)


class WittySelect(WittyEntity, SelectEntity):
    """Ein Register mit wenigen, benannten Werten."""

    entity_description: WittySelectEntityDescription

    @property
    def current_option(self) -> str | None:
        """Gibt die aktuelle Option zurück."""
        raw = self.coordinator.data.get(self.entity_description.key)
        return self.entity_description.options_map.get(raw)

    async def async_select_option(self, option: str) -> None:
        """Schreibe die gewählte Option in die Wallbox."""
        reverse = {name: raw for raw, name in self.entity_description.options_map.items()}
        await self.coordinator.async_write_value(self.entity_description.key, reverse[option])
