"""Support for Hager Witty Solar sensors."""
from __future__ import annotations

import logging
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: config_entries.ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Witty Solar sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    sensors = [
        WittySensor(coordinator, "Control Pilot State", "cp_state", None, None),
        WittySensor(coordinator, "PWM Value", "pwm_value", "%", SensorStateClass.MEASUREMENT),
        WittySensor(coordinator, "Current Phase 1", "current_p1", UnitOfElectricCurrent.AMPERE, SensorStateClass.MEASUREMENT),
        WittySensor(coordinator, "Current Phase 2", "current_p2", UnitOfElectricCurrent.AMPERE, SensorStateClass.MEASUREMENT),
        WittySensor(coordinator, "Current Phase 3", "current_p3", UnitOfElectricCurrent.AMPERE, SensorStateClass.MEASUREMENT),
        WittySensor(coordinator, "Voltage Phase 1", "voltage_p1", UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT),
        WittySensor(coordinator, "Voltage Phase 2", "voltage_p2", UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT),
        WittySensor(coordinator, "Voltage Phase 3", "voltage_p3", UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT),
        WittySensor(coordinator, "Power Phase 1", "power_p1", UnitOfPower.WATT, SensorStateClass.MEASUREMENT),
        WittySensor(coordinator, "Power Phase 2", "power_p2", UnitOfPower.WATT, SensorStateClass.MEASUREMENT),
        WittySensor(coordinator, "Power Phase 3", "power_p3", UnitOfPower.WATT, SensorStateClass.MEASUREMENT),
        WittySensor(coordinator, "Energy Session", "energy_session", UnitOfEnergy.WATT_HOUR, SensorStateClass.TOTAL_INCREASING),
        WittySensor(coordinator, "Error Code", "error_code", None, None),
        WittySensor(coordinator, "RFID Tag UID", "rfid_tag_uid", None, None),
        WittySensor(coordinator, "Boost/Solar Mode", "boost_solar_mode", None, None),
        WittySensor(coordinator, "Firmware Version", "software_version", None, None),
    ]
    
    async_add_entities(sensors)

class WittySensor(CoordinatorEntity, SensorEntity):
    """Representation of a Witty Solar Sensor."""

    def __init__(self, coordinator, name, key, unit, state_class):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = f"Witty Solar {name}"
        self._key = key
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = state_class
        self._attr_unique_id = f"witty_solar_{key}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._key)