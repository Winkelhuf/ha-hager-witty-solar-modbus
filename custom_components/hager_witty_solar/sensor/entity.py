"""Basis-Sensor-Klasse für Hager Witty."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity

from ..entity.base import WittyEntity
from .descriptions import WittySensorEntityDescription


class WittySensor(WittyEntity, SensorEntity):
    """Ein Wert aus coordinator.data (Register oder abgeleiteter Wert)."""

    entity_description: WittySensorEntityDescription

    def __init__(self, coordinator, description: WittySensorEntityDescription) -> None:
        """Initialisiere den Sensor."""
        super().__init__(coordinator, description, description.data_key)

    @property
    def native_value(self) -> Any:
        """Gibt den aktuellen Wert aus dem Coordinator zurück."""
        description = self.entity_description
        raw = self.coordinator.data.get(description.key)
        if raw is None:
            return None
        if description.value_fn is not None:
            raw = description.value_fn(raw)
        if description.state_map is not None:
            # ENUM sensors may only report values from their option list;
            # unknown register values are shown as "unknown".
            return description.state_map.get(raw)
        return raw
