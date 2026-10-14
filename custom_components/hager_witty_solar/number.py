"""Support for Hager Witty Solar number controls."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, REG_MAX_CHARGING_CURRENT, REG_MAX_CHARGING_CURRENT_FB, REG_LED_INTENSITY
from .coordinator.base import WittySolarDataUpdateCoordinator
from .entity.base import WittySolarEntity

async def async_setup_entities(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    pass

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Witty Solar number entities."""
    coordinator: WittySolarDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    numbers = [
        WittySolarNumber(coordinator, "Maximum Charging Current", "max_charging_current", REG_MAX_CHARGING_CURRENT, 6, 32, 1, UnitOfElectricCurrent.AMPERE),
        WittySolarNumber(coordinator, "Maximum Charging Current Fallback", "max_charging_current_fb", REG_MAX_CHARGING_CURRENT_FB, 6, 32, 1, UnitOfElectricCurrent.AMPERE),
        WittySolarNumber(coordinator, "LED Intensity", "led_intensity", REG_LED_INTENSITY, 30, 100, 1, "%"),
    ]

    async_add_entities(numbers)

class WittySolarNumber(WittySolarEntity, NumberEntity):
    """Representation of a Witty Solar Number control."""

    def __init__(self, coordinator: WittySolarDataUpdateCoordinator, name: str, key: str, register: int, min_val: float, max_val: float, step: float, unit: str) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, name, key)
        self._key = key
        self._register = register
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        val = self.coordinator.data.get(self._key)
        return float(val) if val is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value on the device via Modbus."""
        await self.coordinator.async_write_register(self._register, int(value))