"""Button-Plattform: Uhrzeit der Witty synchronisieren."""

from __future__ import annotations

import time

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .data import WittyConfigEntry
from .entity import WittyEntity

PARALLEL_UPDATES = 1

BUTTON_DESCRIPTIONS: tuple[ButtonEntityDescription, ...] = (
    ButtonEntityDescription(key="sync_time", entity_category=EntityCategory.CONFIG),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WittyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Richte die Button-Plattform ein."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(WittyButton(coordinator, description) for description in BUTTON_DESCRIPTIONS)


class WittyButton(WittyEntity, ButtonEntity):
    """Schreibt die aktuelle UTC-Zeit (Unix-Sekunden) in Register 0x3000."""

    entity_description: ButtonEntityDescription

    @property
    def available(self) -> bool:
        """Der Button hängt nur an der Verbindung, nicht an einem gelesenen Wert."""
        return self.coordinator.last_update_success

    async def async_press(self) -> None:
        """Uhrzeit der Wallbox setzen."""
        await self.coordinator.async_write_value("wallbox_time", int(time.time()))
