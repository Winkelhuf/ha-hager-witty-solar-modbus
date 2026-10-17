"""Sensor-Plattform für die Witty-Solar-Wallbox."""
from __future__ import annotations

import logging

from dataclasses import dataclass
import time
from datetime import datetime, timezone
from typing import Any, Callable

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import WittySolarEntity
from .registers import (
    ACCESS_CONTROL_MAP,
    LED_MODE_MAP,
    CP_STATES,
    ERROR_CODE_MAP,
    HARDWARE_CONFIG_MAP,
    CP_STATE_OPTIONS,
    HARDWARE_CURRENT_LIMIT_MAP,
    hardware_limit_amps,
    PULSE_WEIGHT_MAP,
    SESSION_STATE_MAP,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class WittySolarSensorEntityDescription(SensorEntityDescription):
    """Beschreibung eines Witty-Solar-Sensors."""


def _enum_lookup(mapping: dict[int, str]) -> Callable[[dict[str, Any], str], str | None]:
    """Baut eine Lookup-Funktion, die einen Rohwert über ein Mapping in einen Text übersetzt."""

    def _lookup(data: dict[str, Any], key: str) -> str | None:
        raw = data.get(key)
        if raw is None:
            return None
        # Unbekannte Rohwerte -> None (ein ENUM-Sensor darf nur seine Optionen oder None melden).
        return mapping.get(int(raw))

    return _lookup


def _unix_to_datetime(data: dict[str, Any], key: str) -> datetime | None:
    """Wandelt ein Unix-Timestamp-Register in ein datetime um.

    0 (noch nicht gesetzt) und 0xFFFFFFFF (laut Spec: Session läuft noch,
    kein Stop-Zeitpunkt) werden beide als "kein Wert" behandelt.
    """
    raw = data.get(key)
    if not raw or raw == 0xFFFFFFFF:
        return None
    return datetime.fromtimestamp(raw, tz=timezone.utc)


SENSOR_DESCRIPTIONS: tuple[WittySolarSensorEntityDescription, ...] = (
    WittySolarSensorEntityDescription(
        key="cp_state",
        translation_key="cp_state",
        device_class=SensorDeviceClass.ENUM,
        options=list(CP_STATE_OPTIONS),
        icon="mdi:ev-plug-type2",
    ),
    WittySolarSensorEntityDescription(
        key="led_mode",
        translation_key="led_mode",
        device_class=SensorDeviceClass.ENUM,
        options=sorted(set(LED_MODE_MAP.values())),
        icon="mdi:weather-sunny",
    ),
    WittySolarSensorEntityDescription(
        key="session_state",
        translation_key="session_state",
        device_class=SensorDeviceClass.ENUM,
        options=sorted(set(SESSION_STATE_MAP.values())),
    ),
    WittySolarSensorEntityDescription(
        key="error_code",
        translation_key="error_code",
        device_class=SensorDeviceClass.ENUM,
        options=sorted(set(ERROR_CODE_MAP.values())),
    ),
    WittySolarSensorEntityDescription(
        key="access_control",
        translation_key="access_control",
        device_class=SensorDeviceClass.ENUM,
        options=sorted(set(ACCESS_CONTROL_MAP.values())),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WittySolarSensorEntityDescription(
        key="hardware_config",
        translation_key="hardware_config",
        device_class=SensorDeviceClass.ENUM,
        options=sorted(set(HARDWARE_CONFIG_MAP.values())),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WittySolarSensorEntityDescription(
        key="pulse_weight",
        translation_key="pulse_weight",
        device_class=SensorDeviceClass.ENUM,
        options=sorted(set(PULSE_WEIGHT_MAP.values())),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WittySolarSensorEntityDescription(
        key="current_l1",
        translation_key="current_l1",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    WittySolarSensorEntityDescription(
        key="current_l2",
        translation_key="current_l2",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    WittySolarSensorEntityDescription(
        key="current_l3",
        translation_key="current_l3",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    WittySolarSensorEntityDescription(
        key="voltage_l1",
        translation_key="voltage_l1",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WittySolarSensorEntityDescription(
        key="voltage_l2",
        translation_key="voltage_l2",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WittySolarSensorEntityDescription(
        key="voltage_l3",
        translation_key="voltage_l3",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WittySolarSensorEntityDescription(
        key="power_total",
        translation_key="power_total",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    WittySolarSensorEntityDescription(
        key="energy_session",
        translation_key="energy_session",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        # Zähler setzt sich pro Session auf 0 zurück -> total_increasing erkennt den Reset korrekt.
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
    ),
    WittySolarSensorEntityDescription(
        key="timestamp_start_session",
        translation_key="timestamp_start_session",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WittySolarSensorEntityDescription(
        key="timestamp_stop_session",
        translation_key="timestamp_stop_session",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WittySolarSensorEntityDescription(
        key="hw_current_limit",
        translation_key="hw_current_limit",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WittySolarSensorEntityDescription(
        key="max_current_pp",
        translation_key="max_current_pp",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    WittySolarSensorEntityDescription(
        key="rfid_tag_uid",
        translation_key="rfid_tag_uid",
        icon="mdi:card-account-details",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

_ENUM_LOOKUPS: dict[str, Callable[[dict[str, Any], str], str | None]] = {
    "led_mode": _enum_lookup(LED_MODE_MAP),
    "session_state": _enum_lookup(SESSION_STATE_MAP),
    "error_code": _enum_lookup(ERROR_CODE_MAP),
    "access_control": _enum_lookup(ACCESS_CONTROL_MAP),
    "hardware_config": _enum_lookup(HARDWARE_CONFIG_MAP),
    "pulse_weight": _enum_lookup(PULSE_WEIGHT_MAP),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Richte die Sensor-Plattform ein."""
    coordinator = entry.runtime_data.coordinator
    _LOGGER.info("Witty Solar: richte Plattform %s ein", __name__.rsplit(".", 1)[-1])
    entities: list[SensorEntity] = [
        WittySolarSensor(coordinator, description, entry.entry_id) for description in SENSOR_DESCRIPTIONS
    ]
    entities.append(WittySolarEnergyTotalSensor(coordinator, ENERGY_TOTAL_DESCRIPTION, entry.entry_id))
    async_add_entities(entities)


class WittySolarSensor(WittySolarEntity, SensorEntity):
    """Ein einzelner Sensor der Witty-Solar-Wallbox."""

    entity_description: WittySolarSensorEntityDescription

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Kennzeichnet eine aus Strömen geschätzte Ladeleistung (kein Leistungsmesser vorhanden)."""
        if self.entity_description.key == "power_total":
            return {"estimated": self.coordinator.data.get("power_estimated")}
        return None

    @property
    def native_value(self) -> Any:
        """Gibt den aktuellen Wert zurück (ggf. über Enum-Mapping/Umrechnung)."""
        key = self.entity_description.key
        data = self.coordinator.data

        if key == "cp_state":
            raw = data.get(key)
            return raw.lower() if raw in CP_STATES else None

        if key == "power_total":
            return data.get("power_charging")

        if key == "hw_current_limit":
            raw = data.get("hw_current_limit_raw")
            return hardware_limit_amps(raw)

        if key in ("timestamp_start_session", "timestamp_stop_session"):
            return _unix_to_datetime(data, key)

        lookup = _ENUM_LOOKUPS.get(key)
        if lookup:
            return lookup(data, key)

        return data.get(key)


ENERGY_TOTAL_DESCRIPTION = WittySolarSensorEntityDescription(
    key="energy_charged_total",
    translation_key="energy_charged_total",
    device_class=SensorDeviceClass.ENERGY,
    native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    state_class=SensorStateClass.TOTAL_INCREASING,
    suggested_display_precision=2,
)

# Längere Pausen zwischen zwei Messungen (Ausfall, Neustart) werden nicht hochgerechnet.
MAX_INTEGRATION_GAP_S = 120.0


class WittySolarEnergyTotalSensor(WittySolarEntity, RestoreSensor):
    """Aufsummierte Ladeenergie (kWh) für das Energie-Dashboard.

    Die Wallbox liefert auf älterer Firmware weder Gesamtzähler noch Session-Energie.
    Dieser Sensor integriert daher die Ladeleistung (gemessen, sonst aus den Phasenströmen
    geschätzt) über die Zeit und übersteht Neustarts über den gespeicherten Zustand.
    """

    entity_description: WittySolarSensorEntityDescription

    def __init__(self, coordinator, description, entry_id) -> None:
        super().__init__(coordinator, description, entry_id)
        self._total_kwh = 0.0
        self._last_time: float | None = None
        self._last_power: float | None = None

    async def async_added_to_hass(self) -> None:
        """Stellt den zuletzt gespeicherten Zählerstand wieder her."""
        await super().async_added_to_hass()
        last = await self.async_get_last_sensor_data()
        if last is not None and last.native_value is not None:
            try:
                self._total_kwh = float(last.native_value)
            except (TypeError, ValueError):
                self._total_kwh = 0.0

    @callback
    def _handle_coordinator_update(self) -> None:
        now = time.monotonic()
        power = self.coordinator.data.get("power_charging")
        if power is not None and self._last_time is not None and self._last_power is not None:
            elapsed = now - self._last_time
            if 0 < elapsed <= MAX_INTEGRATION_GAP_S:
                average_w = (self._last_power + power) / 2
                self._total_kwh += average_w * elapsed / 3_600_000
        self._last_time = now
        self._last_power = power
        super()._handle_coordinator_update()

    @property
    def native_value(self) -> float:
        return round(self._total_kwh, 3)
