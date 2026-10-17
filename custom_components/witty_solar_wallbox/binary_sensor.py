"""Binary-Sensor-Plattform für die Witty-Solar-Wallbox (reine Lese-Coils)."""
from __future__ import annotations

import logging

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import WittySolarEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class WittySolarBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Beschreibung eines Witty-Solar-Binary-Sensors."""


BINARY_SENSOR_DESCRIPTIONS: tuple[WittySolarBinarySensorEntityDescription, ...] = (
    WittySolarBinarySensorEntityDescription(
        key="vehicle_connected",
        translation_key="vehicle_connected",
        device_class=BinarySensorDeviceClass.PLUG,
    ),
    WittySolarBinarySensorEntityDescription(
        key="charging",
        translation_key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
    ),
    WittySolarBinarySensorEntityDescription(
        key="datetime_not_set",
        translation_key="datetime_not_set",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WittySolarBinarySensorEntityDescription(
        key="pulse_inconsistency",
        translation_key="pulse_inconsistency",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WittySolarBinarySensorEntityDescription(
        key="rfid_reader_configured",
        translation_key="rfid_reader_configured",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WittySolarBinarySensorEntityDescription(
        key="type_ef_occupied",
        translation_key="type_ef_occupied",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WittySolarBinarySensorEntityDescription(
        key="key_position",
        translation_key="key_position",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Richte die Binary-Sensor-Plattform ein."""
    coordinator = entry.runtime_data.coordinator
    _LOGGER.info("Witty Solar: richte Plattform %s ein", __name__.rsplit(".", 1)[-1])
    async_add_entities(
        WittySolarBinarySensor(coordinator, description, entry.entry_id)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class WittySolarBinarySensor(WittySolarEntity, BinarySensorEntity):
    """Ein einzelner Binary-Sensor der Witty-Solar-Wallbox."""

    entity_description: WittySolarBinarySensorEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Gibt den aktuellen Coil-Zustand zurück."""
        return self.coordinator.data.get(self.entity_description.key)
