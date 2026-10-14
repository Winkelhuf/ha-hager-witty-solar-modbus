"""Binärsensor-Plattform für die Hager Witty Modbus Integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .data import WittyConfigEntry
from .entity import WittyEntity

PARALLEL_UPDATES = 0

# Die Werte "charging", "vehicle_connected" und "error" werden in
# registers.derive_values() aus Status- bzw. CP-Register abgeleitet.
BINARY_SENSOR_DESCRIPTIONS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(key="charging", device_class=BinarySensorDeviceClass.BATTERY_CHARGING),
    BinarySensorEntityDescription(key="vehicle_connected", device_class=BinarySensorDeviceClass.PLUG),
    BinarySensorEntityDescription(key="error", device_class=BinarySensorDeviceClass.PROBLEM),
    BinarySensorEntityDescription(key="time_set", entity_category=EntityCategory.DIAGNOSTIC),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WittyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Richte die Binärsensor-Plattform ein."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(WittyBinarySensor(coordinator, description) for description in BINARY_SENSOR_DESCRIPTIONS)


class WittyBinarySensor(WittyEntity, BinarySensorEntity):
    """Ein Ja/Nein-Wert der Wallbox."""

    entity_description: BinarySensorEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Gibt den aktuellen Zustand zurück."""
        value = self.coordinator.data.get(self.entity_description.key)
        return None if value is None else bool(value)
