"""Number-Plattform: einstellbare Ladeströme der Witty."""

from __future__ import annotations

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory, UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .data import WittyConfigEntry
from .entity import WittyEntity

# Schreibzugriffe nacheinander ausführen (die Wallbox erlaubt nur eine Verbindung).
PARALLEL_UPDATES = 1

# Register: Faktor 0,1 A, Wertebereich 0-320 (= 0-32 A). Die PWM-Auflösung der
# Wallbox beträgt 0,6 A - feinere Werte werden von der Wallbox gerundet.
NUMBER_DESCRIPTIONS: tuple[NumberEntityDescription, ...] = (
    NumberEntityDescription(
        key="max_current",
        device_class=NumberDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        native_min_value=0,
        native_max_value=32,
        native_step=0.1,
        mode=NumberMode.BOX,
    ),
    NumberEntityDescription(
        key="max_current_fallback",
        device_class=NumberDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        native_min_value=0,
        native_max_value=32,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WittyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Richte die Number-Plattform ein."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(WittyNumber(coordinator, description) for description in NUMBER_DESCRIPTIONS)


class WittyNumber(WittyEntity, NumberEntity):
    """Ein beschreibbares Register (Ladestrom in A)."""

    entity_description: NumberEntityDescription

    @property
    def native_value(self) -> float | None:
        """Gibt den aktuell gesetzten Wert zurück."""
        return self.coordinator.data.get(self.entity_description.key)

    async def async_set_native_value(self, value: float) -> None:
        """Schreibe den neuen Wert in die Wallbox."""
        await self.coordinator.async_write_value(self.entity_description.key, value)
