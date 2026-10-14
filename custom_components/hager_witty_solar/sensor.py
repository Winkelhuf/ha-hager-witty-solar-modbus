"""Support for Hager Witty Solar sensors."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator.base import WittySolarDataUpdateCoordinator
from .entity.base import WittySolarEntity
from .sensor.descriptions import SENSOR_TYPES, WittySensorEntityDescription

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Witty Solar sensors based on a config entry."""
    coordinator: WittySolarDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        WittySolarSensor(coordinator, description)
        for description in SENSOR_TYPES
    ]

    async_add_entities(entities)

class WittySolarSensor(WittySolarEntity, SensorEntity):
    """Representation of a Witty Solar Sensor."""

    entity_description: WittySensorEntityDescription

    def __init__(self, coordinator: WittySolarDataUpdateCoordinator, description: WittySensorEntityDescription) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description.name, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self.entity_description.key_mapping)