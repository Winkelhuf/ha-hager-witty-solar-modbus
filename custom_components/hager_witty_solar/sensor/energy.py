"""Berechneter Gesamt-Energiezähler (kWh) für das Home Assistant Energie-Dashboard.

Die Witty liefert per Modbus nur die Energie der AKTUELLEN Ladesession (Wh, wird mit
jeder neuen Session auf 0 zurückgesetzt), aber keinen Gesamtzähler. Das
Energie-Dashboard braucht jedoch einen dauerhaft steigenden Zähler. Dieser Sensor
summiert deshalb die Zuwächse des Session-Registers auf:

* Wert steigt (oder bleibt gleich)  -> Differenz wird addiert (gleiche Session)
* Wert fällt                         -> neue Session, der neue Wert wird addiert

Der Zählerstand und der zuletzt gesehene Session-Wert werden über Neustarts hinweg
wiederhergestellt, damit auch Energie, die während eines Home-Assistant-Neustarts
in einer laufenden Session geladen wurde, korrekt nachgetragen wird.

Grenzen: Beginnt zwischen zwei Abfragen (z. B. während HA offline ist) eine neue
Session, deren Energie den letzten Session-Wert bereits übersteigt, wird nur die
Differenz gezählt. Das betrifft ausschließlich lange Abfragelücken.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.core import callback
from homeassistant.helpers.restore_state import ExtraStoredData, RestoredExtraData, RestoreEntity

from ..entity.base import WittyEntity


@dataclass(frozen=True, kw_only=True)
class WittyEnergyEntityDescription(SensorEntityDescription):
    """Beschreibt einen aus einem Session-Register abgeleiteten Energiezähler."""

    source_key: str
    """Key des Session-Energie-Registers (Wh) in coordinator.data."""


ENERGY_ENTITY_DESCRIPTIONS: tuple[WittyEnergyEntityDescription, ...] = (
    WittyEnergyEntityDescription(
        key="energy_total",
        source_key="session_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    ),
)


class WittyEnergyTotalSensor(WittyEntity, SensorEntity, RestoreEntity):
    """Dauerhaft steigender kWh-Zähler, berechnet aus der Session-Energie."""

    entity_description: WittyEnergyEntityDescription

    def __init__(self, coordinator, description: WittyEnergyEntityDescription) -> None:
        """Initialisiere den Energiesensor."""
        super().__init__(coordinator, description, description.source_key)
        self._total_wh: float = 0.0
        self._last_session_wh: int | None = None

    async def async_added_to_hass(self) -> None:
        """Zählerstand und letzten Session-Wert wiederherstellen.

        Die Listener-Registrierung beim Coordinator übernimmt bereits
        CoordinatorEntity.async_added_to_hass() über super().
        """
        await super().async_added_to_hass()

        extra = await self.async_get_last_extra_data()
        if extra is not None:
            stored = extra.as_dict()
            try:
                self._total_wh = float(stored.get("total_wh") or 0.0)
                last = stored.get("last_session_wh")
                self._last_session_wh = None if last is None else int(last)
            except (TypeError, ValueError):
                self._total_wh, self._last_session_wh = 0.0, None

        # Session-Wert, der beim Einrichten bereits vorliegt, sofort verarbeiten.
        self._accumulate()

    @property
    def extra_restore_state_data(self) -> ExtraStoredData:
        """Zusätzlich zum Zählerstand den letzten Session-Wert sichern."""
        return RestoredExtraData({"total_wh": self._total_wh, "last_session_wh": self._last_session_wh})

    @property
    def native_value(self) -> float:
        """Aktueller Zählerstand in kWh."""
        return round(self._total_wh / 1000, 4)

    def _accumulate(self) -> None:
        """Neuen Session-Wert einlesen und den Gesamtzähler fortschreiben."""
        current: Any = self.coordinator.data.get(self.entity_description.source_key)
        if current is None:
            return
        current = int(current)

        if self._last_session_wh is None:
            pass  # erster Wert überhaupt: nur als Ausgangspunkt merken
        elif current >= self._last_session_wh:
            self._total_wh += current - self._last_session_wh
        else:
            self._total_wh += current  # Register wurde zurückgesetzt: neue Session
        self._last_session_wh = current

    @callback
    def _handle_coordinator_update(self) -> None:
        """Neuen Wert verarbeiten und den Zustand schreiben."""
        self._accumulate()
        super()._handle_coordinator_update()
