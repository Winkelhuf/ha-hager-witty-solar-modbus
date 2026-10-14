"""Sensor descriptions for Hager Witty Solar."""
from __future__ import annotations

from dataclasses import dataclass
from homeassistant.components.sensor import SensorEntityDescription, SensorStateClass
from homeassistant.const import UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfEnergy, UnitOfPower

@dataclass
class WittySensorEntityDescription(SensorEntityDescription):
    """Class describing Witty Solar sensor entities."""
    key_mapping: str = ""

SENSOR_TYPES: tuple[WittySensorEntityDescription, ...] = (
    WittySensorEntityDescription(
        key="cp_state",
        name="Control Pilot State",
        key_mapping="cp_state",
    ),
    WittySensorEntityDescription(
        key="pwm_value",
        name="PWM Value",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        key_mapping="pwm_value",
    ),
    WittySensorEntityDescription(
        key="current_phase_1",
        name="Current Phase 1",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        key_mapping="current_phase_1",
    ),
    WittySensorEntityDescription(
        key="current_phase_2",
        name="Current Phase 2",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        key_mapping="current_phase_2",
    ),
    WittySensorEntityDescription(
        key="current_phase_3",
        name="Current Phase 3",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        key_mapping="current_phase_3",
    ),
    WittySensorEntityDescription(
        key="voltage_phase_1",
        name="Voltage Phase 1",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        key_mapping="voltage_phase_1",
    ),
    WittySensorEntityDescription(
        key="voltage_phase_2",
        name="Voltage Phase 2",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        key_mapping="voltage_phase_2",
    ),
    WittySensorEntityDescription(
        key="voltage_phase_3",
        name="Voltage Phase 3",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        key_mapping="voltage_phase_3",
    ),
    WittySensorEntityDescription(
        key="power_phase_1",
        name="Power Phase 1",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        key_mapping="power_phase_1",
    ),
    WittySensorEntityDescription(
        key="power_phase_2",
        name="Power Phase 2",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        key_mapping="power_phase_2",
    ),
    WittySensorEntityDescription(
        key="power_phase_3",
        name="Power Phase 3",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        key_mapping="power_phase_3",
    ),
    WittySensorEntityDescription(
        key="energy_session",
        name="Energy Session",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        key_mapping="energy_session",
    ),
    WittySensorEntityDescription(
        key="error_code",
        name="Error Code",
        key_mapping="error_code",
    ),
)