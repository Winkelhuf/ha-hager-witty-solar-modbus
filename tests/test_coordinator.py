"""Logik-Tests des Coordinators ohne Netzwerk und ohne laufendes Home Assistant."""
from __future__ import annotations

import pytest

from homeassistant.exceptions import HomeAssistantError

from custom_components.witty_solar_wallbox.coordinator import WittySolarCoordinator

derive = WittySolarCoordinator._derive_values
check_write = WittySolarCoordinator._check_write


def _base(**overrides):
    data = {
        "cp_state": "C2",
        "current_l1": 8.5,
        "current_l2": None,
        "current_l3": None,
        "voltage_l1": None,
        "voltage_l2": None,
        "voltage_l3": None,
        "power_l1": None,
        "power_l2": None,
        "power_l3": None,
    }
    data.update(overrides)
    return data


def test_charging_state_connected_and_estimated_power() -> None:
    """C2 mit Strom: Fahrzeug verbunden, lädt; Leistung wird ohne Messung aus Strom x 230 V geschätzt."""
    data = _base()
    derive(data)
    assert data["vehicle_connected"] is True
    assert data["charging"] is True
    assert data["power_charging"] == round(8.5 * 230)
    assert data["power_estimated"] is True


def test_measured_power_wins_over_estimate() -> None:
    """Gemessene Leistung hat Vorrang vor der Schätzung."""
    data = _base(power_l1=1960)
    derive(data)
    assert data["power_charging"] == 1960
    assert data["power_estimated"] is False


def test_measured_voltage_is_used_for_estimate() -> None:
    """Liegt eine Spannung vor, wird sie statt 230 V verwendet."""
    data = _base(voltage_l1=240.0)
    derive(data)
    assert data["power_charging"] == round(8.5 * 240.0)


@pytest.mark.parametrize(
    ("cp_state", "connected", "charging"),
    [
        ("A1", False, False),
        ("A2", False, False),
        ("B1", True, False),
        ("B2", True, False),
        ("C1", True, False),
        ("C2", True, True),
        ("E", None, False),
        ("F", None, False),
    ],
)
def test_vehicle_connected_and_charging_from_cp_state(cp_state: str, connected: bool | None, charging: bool) -> None:
    """Zuordnung CP-Zustand -> angeschlossen / lädt."""
    data = _base(cp_state=cp_state)
    derive(data)
    assert data["vehicle_connected"] is connected
    assert data["charging"] is charging


def test_c2_without_current_is_not_charging() -> None:
    """C2 allein beweist keinen Stromfluss: bei 0 A gilt die Wallbox nicht als ladend."""
    data = _base(current_l1=0.0)
    derive(data)
    assert data["charging"] is False
    assert data["power_charging"] == 0


def test_unknown_cp_state_gives_unknown_values() -> None:
    """Ohne gültigen CP-Zustand bleiben die abgeleiteten Werte unbekannt (None)."""
    data = _base(cp_state=None, current_l1=None)
    derive(data)
    assert data["vehicle_connected"] is None
    assert data["charging"] is None
    assert data["power_charging"] is None


def test_check_write_ok_and_failures() -> None:
    """Schreib-Rücklese-Kontrolle: nur 'ok'/'no_readback' sind still, Fehler werden sichtbar."""
    check_write("ok", "Test")
    check_write("no_readback", "Test")
    with pytest.raises(HomeAssistantError):
        check_write("rejected", "Test")
    with pytest.raises(HomeAssistantError):
        check_write("not_applied", "Test")
