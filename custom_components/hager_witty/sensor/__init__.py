"""Sensor-Plattform für die Hager Witty Modbus Integration."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..data import WittyConfigEntry
from .descriptions import SENSOR_DESCRIPTIONS
from .energy import ENERGY_ENTITY_DESCRIPTIONS, WittyEnergyTotalSensor
from .entity import WittySensor

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WittyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Richte die Sensor-Plattform ein."""
    coordinator = entry.runtime_data.coordinator

    entities: list = [WittySensor(coordinator, description) for description in SENSOR_DESCRIPTIONS]
    entities.extend(WittyEnergyTotalSensor(coordinator, description) for description in ENERGY_ENTITY_DESCRIPTIONS)
    async_add_entities(entities)
