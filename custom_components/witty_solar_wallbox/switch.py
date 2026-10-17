"""Switch-Plattform für die Witty-Solar-Wallbox.

Enthält vier Schalter, alle über Coils gesteuert:
- Station available (0x0001) - Ladestation freigeben/sperren
- Switch3to1 (0x0003) - Phasenumschaltung 3-phasig/1-phasig
- Lock cable (0x0006) - Kabel dauerhaft verriegeln
- RFID-Authentifizierung aktivieren (0x000A)

Der LED-Modus (Register 0x0052, "Boost/Solar mode" in der Spec) ist eine
Select-Entity in select.py - er betrifft nur die HMI-LED.
"""
from __future__ import annotations

import logging

from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEFAULT_MAX_CURRENT_A
from .entity import WittySolarEntity
from .registers import hardware_limit_amps

STATION_AVAILABLE_DESCRIPTION = SwitchEntityDescription(
    key="station_available",
    translation_key="station_available",
    icon="mdi:ev-station",
)

SWITCH_3TO1_DESCRIPTION = SwitchEntityDescription(
    key="switch_3to1",
    translation_key="switch_3to1",
    icon="mdi:sine-wave",
    entity_category=EntityCategory.CONFIG,
)

LOCK_CABLE_DESCRIPTION = SwitchEntityDescription(
    key="lock_cable",
    translation_key="lock_cable",
    icon="mdi:lock-outline",
    entity_category=EntityCategory.CONFIG,
)

BOOST_DESCRIPTION = SwitchEntityDescription(
    key="boost_mode",
    translation_key="boost_mode",
    icon="mdi:rocket-launch",
)

CHARGING_ENABLED_DESCRIPTION = SwitchEntityDescription(
    key="charging_enabled",
    translation_key="charging_enabled",
    icon="mdi:play-pause",
)

RFID_AUTH_DESCRIPTION = SwitchEntityDescription(
    key="rfid_auth_enabled",
    translation_key="rfid_auth_enabled",
    icon="mdi:card-account-details-outline",
    entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Richte die Switch-Plattform ein."""
    coordinator = entry.runtime_data.coordinator
    _LOGGER.info("Witty Solar: richte Plattform %s ein", __name__.rsplit(".", 1)[-1])
    async_add_entities(
        [
            WittySolarStationAvailableSwitch(coordinator, STATION_AVAILABLE_DESCRIPTION, entry.entry_id),
            WittySolarSwitch3to1Switch(coordinator, SWITCH_3TO1_DESCRIPTION, entry.entry_id),
            WittySolarLockCableSwitch(coordinator, LOCK_CABLE_DESCRIPTION, entry.entry_id),
            WittySolarRfidAuthSwitch(coordinator, RFID_AUTH_DESCRIPTION, entry.entry_id),
            WittySolarBoostSwitch(coordinator, BOOST_DESCRIPTION, entry.entry_id),
            WittySolarChargingEnabledSwitch(coordinator, CHARGING_ENABLED_DESCRIPTION, entry.entry_id),
        ]
    )

_LOGGER = logging.getLogger(__name__)


class WittySolarStationAvailableSwitch(WittySolarEntity, SwitchEntity):
    """Gibt die Ladestation frei bzw. sperrt die HMI (Coil 0x0001)."""

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.get("station_available")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_write_station_available(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_write_station_available(False)


class WittySolarSwitch3to1Switch(WittySolarEntity, SwitchEntity):
    """Schaltet zwischen 3-phasigem (aus) und 1-phasigem (an) Laden um (Coil 0x0003)."""

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.get("switch_3to1")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_write_switch_3to1(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_write_switch_3to1(False)


class WittySolarLockCableSwitch(WittySolarEntity, SwitchEntity):
    """Simuliert ein dauerhaft angeschlossenes Kabel (Coil 0x0006).

    Achtung: Ist der Schalter einmal an, bleibt das Kabel laut Spec auch
    nach einem Blackout verriegelt - erst ein erneutes Ausschalten hebt
    die Verriegelung wieder auf.
    """

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.get("lock_cable")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_write_lock_cable(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_write_lock_cable(False)


class WittySolarRfidAuthSwitch(WittySolarEntity, SwitchEntity):
    """Aktiviert/deaktiviert die RFID-Authentifizierung (Coil 0x000A).

    Die Wallbox lehnt das Schreiben ab, solange auf irgendeiner Buchse eine
    Ladesession läuft - das Schalten kann in diesem Fall fehlschlagen.
    """

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.get("rfid_auth_enabled")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_write_rfid_auth_enable(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_write_rfid_auth_enable(False)


class WittySolarBoostSwitch(WittySolarEntity, SwitchEntity):
    """Boost: Maximalstrom (Register 0x0050) auf das Hardware-Limit setzen bzw. zurücknehmen.

    Das Register "Boost/Solar mode" (0x0052) ändert laut Spec nur die HMI-LED (siehe
    select.py). Die tatsächliche Leistung bestimmt der Maximalstrom: Die Wallbox
    liefert Min(Hardware-Limit, Kabel (PP), Maximalstrom). Dieser Schalter bildet
    "volle Leistung" nach, indem er den Maximalstrom auf das Hardware-Limit
    (Codierrad, Register 0x0043) setzt; beim Ausschalten wird der zuvor eingestellte
    Wert wiederhergestellt (nach einem HA-Neustart: 16 A, höchstens das Hardware-Limit).
    """

    _previous_current: float | None = None

    def _hw_limit(self) -> int:
        raw = self.coordinator.data.get("hw_current_limit_raw")
        return hardware_limit_amps(raw) or DEFAULT_MAX_CURRENT_A

    @property
    def is_on(self) -> bool | None:
        current = self.coordinator.data.get("max_charging_current")
        return None if current is None else int(current) >= self._hw_limit()

    async def async_turn_on(self, **kwargs: Any) -> None:
        current = self.coordinator.data.get("max_charging_current")
        if current is not None and int(current) < self._hw_limit():
            self._previous_current = float(current)
        await self.coordinator.async_write_max_current(self._hw_limit())

    async def async_turn_off(self, **kwargs: Any) -> None:
        target = self._previous_current if self._previous_current is not None else min(16, self._hw_limit())
        await self.coordinator.async_write_max_current(int(target))


class WittySolarChargingEnabledSwitch(WittySolarEntity, SwitchEntity):
    """Laden starten/stoppen über den maximalen Ladestrom (Register 0x0050).

    Aus = 0 A (laut Spec gültig und verhindert das Laden), Ein = zuletzt eingestellter
    Strom (nach einem Neustart: 16 A, höchstens das Hardware-Limit). Das ist kein eigener
    Start/Stop-Befehl der Wallbox; ob 0 A bei deiner Firmware das Laden zuverlässig
    pausiert, sollte einmal praktisch geprüft werden.
    """

    _previous_current: float | None = None

    def _hw_limit(self) -> int:
        return hardware_limit_amps(self.coordinator.data.get("hw_current_limit_raw")) or DEFAULT_MAX_CURRENT_A

    @property
    def is_on(self) -> bool | None:
        current = self.coordinator.data.get("max_charging_current")
        return None if current is None else int(current) > 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        target = self._previous_current if self._previous_current else min(16, self._hw_limit())
        await self.coordinator.async_write_max_current(int(target))

    async def async_turn_off(self, **kwargs: Any) -> None:
        current = self.coordinator.data.get("max_charging_current")
        if current:
            self._previous_current = float(current)
        await self.coordinator.async_write_max_current(0)
