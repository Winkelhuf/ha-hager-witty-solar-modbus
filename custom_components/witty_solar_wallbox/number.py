"""Number-Plattform für die Witty-Solar-Wallbox (Ladestrom, LED-Helligkeit)."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import WittySolarEntity
from .registers import hardware_limit_amps

MAX_CURRENT_DESCRIPTION = NumberEntityDescription(
    key="max_charging_current",
    translation_key="max_charging_current",
    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
    native_min_value=0.0,
    native_max_value=32.0,
    native_step=1.0,
    mode=NumberMode.SLIDER,
    icon="mdi:current-ac",
)

LED_INTENSITY_DESCRIPTION = NumberEntityDescription(
    key="led_intensity",
    translation_key="led_intensity",
    native_unit_of_measurement=PERCENTAGE,
    native_min_value=30.0,
    native_max_value=100.0,
    native_step=1.0,
    mode=NumberMode.SLIDER,
    icon="mdi:led-on",
    entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Richte die Number-Plattform ein."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        [
            WittySolarMaxCurrentNumber(coordinator, MAX_CURRENT_DESCRIPTION, entry.entry_id),
            WittySolarLedIntensityNumber(coordinator, LED_INTENSITY_DESCRIPTION, entry.entry_id),
        ]
    )


MIN_CHARGING_CURRENT_A = 6  # IEC 61851: unter 6 A darf kein PWM-Signal ausgegeben werden


class WittySolarMaxCurrentNumber(WittySolarEntity, NumberEntity):
    """Maximaler Ladestrom (Register 0x0050), begrenzt durch das Hardware-Limit der Wallbox.

    0 A ist laut Spec (§3.3.26.2) ein gültiger Wert und pausiert/verbietet das Laden
    (nützlich z. B. beim Überschussladen ohne Sonne). Werte von 1-5 A liegen unter dem
    IEC-61851-Minimum von 6 A und werden abgelehnt.
    """

    @property
    def native_max_value(self) -> float:
        """Nutzt das ausgelesene Hardware-Limit (Register 0x0043) als Obergrenze, falls bekannt."""
        raw = self.coordinator.data.get("hw_current_limit_raw")
        hw_limit = hardware_limit_amps(raw)
        return float(hw_limit) if hw_limit else self.entity_description.native_max_value

    @property
    def native_value(self) -> float | None:
        """Aktuell eingestellter maximaler Ladestrom."""
        return self.coordinator.data.get("max_charging_current")

    async def async_set_native_value(self, value: float) -> None:
        """Schreibt den neuen maximalen Ladestrom auf die Wallbox."""
        amps = int(round(value))
        if 0 < amps < MIN_CHARGING_CURRENT_A:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="current_below_minimum",
                translation_placeholders={"minimum": str(MIN_CHARGING_CURRENT_A)},
            )
        await self.coordinator.async_write_max_current(amps)


class WittySolarLedIntensityNumber(WittySolarEntity, NumberEntity):
    """LED-Helligkeit der HMI (Register 0x0066, 30-100%)."""

    @property
    def native_value(self) -> float | None:
        """Aktuell eingestellte LED-Helligkeit."""
        return self.coordinator.data.get("led_intensity")

    async def async_set_native_value(self, value: float) -> None:
        """Schreibt die neue LED-Helligkeit auf die Wallbox."""
        await self.coordinator.async_write_led_intensity(int(round(value)))
