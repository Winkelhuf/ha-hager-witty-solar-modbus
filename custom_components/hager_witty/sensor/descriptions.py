"""Sensor descriptions for the Hager Witty Modbus integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTime,
)

from ..registers import (
    BADGE_TYPES,
    CP_STATES,
    LOCK_STATES,
    SESSION_STATES,
    STOP_REASONS,
    WALLBOX_STATUS,
)


def _timestamp(value: int) -> datetime | None:
    """Unix seconds (UTC) -> datetime, 0 / nonsense -> None."""
    if not value:
        return None
    try:
        return datetime.fromtimestamp(value, UTC)
    except (OverflowError, OSError, ValueError):
        return None


@dataclass(frozen=True, kw_only=True)
class WittySensorEntityDescription(SensorEntityDescription):
    """Description of a sensor backed by a value in coordinator.data."""

    data_key: str | None = None
    """Key that must exist in coordinator.data for the sensor to be available
    (defaults to ``key``)."""
    state_map: dict[Any, str] | None = None
    """Raw value -> option key (ENUM sensors). Unknown raw values give ``unknown``."""
    value_fn: Callable[[Any], Any] | None = None
    """Optional conversion of the raw value."""


def _enum(key: str, states: dict[Any, str], **kwargs: Any) -> WittySensorEntityDescription:
    """ENUM sensor whose texts come from translations (entity.sensor.<key>.state.*)."""
    return WittySensorEntityDescription(
        key=key,
        device_class=SensorDeviceClass.ENUM,
        options=list(dict.fromkeys(states.values())),
        state_map=states,
        **kwargs,
    )


def _phase(prefix: str, unit: str, device_class: SensorDeviceClass, precision: int) -> list[WittySensorEntityDescription]:
    return [
        WittySensorEntityDescription(
            key=f"{prefix}_l{phase}",
            device_class=device_class,
            native_unit_of_measurement=unit,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=precision,
        )
        for phase in (1, 2, 3)
    ]


SENSOR_DESCRIPTIONS: tuple[WittySensorEntityDescription, ...] = (
    # --- state -------------------------------------------------------------------
    _enum("status", WALLBOX_STATUS),
    _enum("cp_state", {state: state for state in CP_STATES}, value_fn=lambda raw: str(raw).lower()),
    _enum("lock_state", LOCK_STATES),
    _enum("session_state", SESSION_STATES),
    _enum("stop_reason", STOP_REASONS),
    # --- power / current / voltage ---------------------------------------------
    WittySensorEntityDescription(
        key="power_total",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    *_phase("power", UnitOfPower.WATT, SensorDeviceClass.POWER, 0),
    *_phase("current", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, 1),
    *_phase("voltage", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, 1),
    # --- session -------------------------------------------------------------------
    WittySensorEntityDescription(
        key="session_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        # Counts up during a session and jumps back to 0 with the next one.
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    ),
    WittySensorEntityDescription(
        key="charge_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.MINUTES,
        suggested_display_precision=0,
    ),
    WittySensorEntityDescription(
        key="session_start",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_timestamp,
    ),
    WittySensorEntityDescription(
        key="session_stop",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_timestamp,
    ),
    WittySensorEntityDescription(
        key="session_badge",
        data_key="session_badge_size",
    ),
    _enum("badge_type", BADGE_TYPES, entity_category=EntityCategory.DIAGNOSTIC),
    # --- diagnostic --------------------------------------------------------------
    WittySensorEntityDescription(
        key="pwm_duty",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
    ),
    WittySensorEntityDescription(
        key="hw_current_limit",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
    ),
    WittySensorEntityDescription(
        key="cable_current_limit",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
    ),
    WittySensorEntityDescription(
        key="rfid_tag",
        data_key="rfid_uid_size",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    WittySensorEntityDescription(
        key="wallbox_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_timestamp,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)
