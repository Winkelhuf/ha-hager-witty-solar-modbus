"""DataUpdateCoordinator für das Hager EVCS-Kommunikationsboard (B1280, Witty Solar)."""
from __future__ import annotations

import time
from datetime import timedelta
from typing import Any

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UNIT_ID
from .registers import (
    COIL_ACK_ENERGY_SESSION,
    COIL_LOCK_CABLE,
    COIL_PROXIMITY_SHORT_PRESS,
    COIL_OFFSET_ACK_ENERGY_SESSION,
    COIL_OFFSET_DATETIME_NOT_SET,
    COIL_OFFSET_DELAY_FALLBACK,
    COIL_OFFSET_KEY_POSITION,
    COIL_OFFSET_LOCK_CABLE,
    COIL_OFFSET_LOOP_GENERIC_BLINK,
    COIL_OFFSET_PROXIMITY_SHORT_PRESS,
    COIL_OFFSET_PULSE_INCONSISTENCY,
    COIL_OFFSET_RFID_AUTH_ENABLE,
    COIL_OFFSET_RFID_READER_CONFIGURED,
    COIL_OFFSET_STATION_AVAILABLE,
    COIL_OFFSET_STATION_AVAILABLE_FALLBACK,
    COIL_OFFSET_SWITCH_3TO1,
    COIL_OFFSET_SWITCH_3TO1_FALLBACK,
    COIL_OFFSET_TYPE_EF_AVAILABILITY,
    COIL_RFID_AUTH_ENABLE,
    COILS_BLOCK_COUNT,
    COILS_BLOCK_START,
    COIL_STATION_AVAILABLE,
    COIL_SWITCH_3TO1,
    CURRENT_INVALID,
    MAGICBYTE_VALUE,
    REG_MAGICBYTE,
    DEVICE_INFO_BLOCK_COUNT,
    DEVICE_INFO_BLOCK_START,
    LIVE_BLOCK_COUNT,
    LIVE_BLOCK_START,
    OFFSET_ACCESS_CONTROL,
    OFFSET_LED_MODE,
    OFFSET_CP_STATE,
    OFFSET_CURRENT_L1,
    OFFSET_CURRENT_L2,
    OFFSET_CURRENT_L3,
    OFFSET_ENERGY_SESSION,
    OFFSET_ERROR_CODE,
    OFFSET_HARDWARE_CONFIG,
    OFFSET_HW_CURRENT_LIMIT,
    OFFSET_LED_INTENSITY,
    OFFSET_MANUFACTURER,
    OFFSET_MAX_CHARGING_CURRENT,
    OFFSET_MAX_CURRENT_PP,
    OFFSET_POWER_L1,
    OFFSET_POWER_L2,
    OFFSET_POWER_L3,
    OFFSET_PRODUCT_REFERENCE,
    OFFSET_PULSE_WEIGHT,
    OFFSET_PWM_VALUE,
    OFFSET_RFID_TAG_UID,
    OFFSET_SERIAL_NUMBER,
    OFFSET_SESSION_STATE,
    OFFSET_SOFTWARE_VERSION,
    OFFSET_TIMESTAMP_START_SESSION,
    OFFSET_TIMESTAMP_STOP_SESSION,
    OFFSET_TIMESTAMP_UNIX,
    OFFSET_VOLTAGE_L1,
    OFFSET_VOLTAGE_L2,
    OFFSET_VOLTAGE_L3,
    REG_LED_MODE,
    REG_LED_INTENSITY,
    REG_MAX_CHARGING_CURRENT,
    REG_TIMESTAMP_UNIX,
    VOLTAGE_POWER_INVALID,
)

import logging

_LOGGER = logging.getLogger(__name__)


def _ascii_block_to_str(registers: list[int]) -> str:
    """Wandelt einen Block von 16-Bit-Registern (2 ASCII-Zeichen je Register) in Text um."""
    raw = bytearray()
    for reg in registers:
        raw.append((reg >> 8) & 0xFF)
        raw.append(reg & 0xFF)
    return raw.decode("utf-8", errors="ignore").strip("\x00").strip()


def _to_signed16(value: int) -> int:
    """Wandelt einen unsigned 16-Bit-Rohwert in einen signed Int16 um."""
    return value - 0x10000 if value >= 0x8000 else value


def _to_uint32(high: int, low: int) -> int:
    """Kombiniert zwei 16-Bit-Register (MSB zuerst) zu einem UInt32."""
    return (high << 16) | low


# Das EVCS-Board setzt die TCP-Verbindung bei großen Leseanfragen zurück -> kleine Blöcke.
MAX_REGISTERS_PER_READ = 16
# (Startadresse, Anzahl, optional) - Pflicht: Messwerte (0x0043) und Konfiguration (0x0050). Alle anderen Bereiche sind optional,
# wie in der funktionierenden Alt-Integration (dort nur Warnung bei Ablehnung).
LIVE_SEGMENTS = (
    (0x0043, 13, False),  # HW-Limit, PP, CP, PWM, Strom/Spannung/Leistung
    (0x0050, 5, False),   # Max-Ladestrom, Fallback, LED-Modus, Zugang, Fehlercode
    (0x0066, 1, True),   # LED-Helligkeit
    (0x0069, 2, True),   # Energie der Session
    (0x006F, 2, True),   # Session-Status, Pulsgewicht
    (0x0055, 16, True),   # RFID-Tag-UID
    (0x0065, 1, True),    # Hardware-Konfiguration
    (0x006B, 4, True),    # Start-/Stop-Zeitstempel
    (0x0071, 2, True),    # Unix-Zeit der Wallbox
)
NOMINAL_VOLTAGE = 230.0  # V je Phase für die Leistungsschätzung ohne Spannungsmessung
RECONNECT_DELAY = 1.0  # Sekunden Wartezeit nach einem Verbindungsabbruch


class WittySolarCoordinator(DataUpdateCoordinator):
    """Verwaltet Datenabruf und Schreibzugriffe für das EVCS-Kommunikationsboard."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, unit_id: int = UNIT_ID) -> None:
        """Initialisierung des Coordinators."""
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.client = ModbusTcpClient(host=host, port=port)
        self.device_info_data: dict[str, Any] = {}
        self._chunk_size = MAX_REGISTERS_PER_READ
        self._handshake_done = False
        self._closed_at = 0.0
        self._unsupported_segments: set[int] = set()
        self._segment_failures: dict[int, int] = {}
        self._unsupported_coils: set[int] = set()

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=10),
        )

    # -- Modbus-Hilfen -----------------------------------------------------

    def _close(self) -> None:
        """Schließt die Verbindung, damit der nächste Poll sauber neu verbindet."""
        self._handshake_done = False
        self._closed_at = time.monotonic()
        try:
            self.client.close()
        except Exception:  # noqa: BLE001 - Aufräumen darf nie selbst fehlschlagen
            pass

    def _ensure_connected(self) -> None:
        """Verbindet (mit Wartezeit nach einem Abbruch) und liest zuerst das Magicbyte.

        Das Board hängt nach einem Reset evtl. noch an der alten Verbindung und lehnt
        sofortige Neuverbindungen ab; zudem klappt der erste Zugriff nachweislich mit dem
        Magicbyte-Register (wie im Verbindungstest), also beginnt jede Verbindung damit.
        """
        if self.client.connected and self._handshake_done:
            return
        wait = RECONNECT_DELAY - (time.monotonic() - self._closed_at)
        if wait > 0:
            time.sleep(wait)
        if not self.client.connected and not self.client.connect():
            raise UpdateFailed(f"Keine Verbindung zur Wallbox unter {self.host}:{self.port}")
        time.sleep(0.3)
        result = self.client.read_holding_registers(REG_MAGICBYTE, count=1, device_id=self.unit_id)
        if result is None or result.isError() or result.registers[0] != MAGICBYTE_VALUE:
            self._close()
            raise UpdateFailed(f"Wallbox {self.host}:{self.port} antwortet nicht mit dem erwarteten Magicbyte")
        self._handshake_done = True

    def _read_registers(self, address: int, count: int) -> list[int]:
        """Liest Holding-Register in kleinen Blöcken.

        Setzt das Board die Verbindung bei einer Anfrage zurück, wird neu verbunden und
        die Blockgröße halbiert (bis hinunter zu 1 Register). Die funktionierende Größe
        wird für die weiteren Polls gemerkt.
        """
        values: list[int] = []
        offset = 0
        while offset < count:
            chunk = min(self._chunk_size, count - offset)
            try:
                self._ensure_connected()
                result = self.client.read_holding_registers(address + offset, count=chunk, device_id=self.unit_id)
            except (OSError, ModbusException) as err:
                self._close()
                if self._chunk_size > 1:
                    self._chunk_size = max(1, self._chunk_size // 2)
                    _LOGGER.debug(
                        "Lesen von 0x%04X (%d Register) fehlgeschlagen (%s); versuche %d Register pro Anfrage",
                        address + offset, chunk, err, self._chunk_size,
                    )
                    continue
                raise UpdateFailed(f"Verbindung zur Wallbox {self.host}:{self.port} unterbrochen: {err}") from err
            if result is None or result.isError():
                raise UpdateFailed(
                    f"Register 0x{address + offset:04X} ({chunk} Stück) konnten nicht gelesen werden ({self.host}:{self.port})"
                )
            values.extend(result.registers[:chunk])
            offset += chunk
        return values

    def _read_live_registers(self) -> list[int]:
        """Liest den Live-Bereich 0x0043..0x0072 in denselben kleinen Segmenten wie die bewährte Alt-Integration.

        Pflicht-Segmente führen bei Fehlern zu UpdateFailed. Optionale Segmente (RFID-UID,
        Hardware-Konfiguration, Zeitstempel) werden bei einem Fehler dauerhaft übersprungen,
        damit ein nicht unterstützter Bereich nicht bei jedem Poll die Verbindung zurücksetzt.
        """
        regs = [0] * LIVE_BLOCK_COUNT
        regs[OFFSET_TIMESTAMP_STOP_SESSION[0]] = 0xFFFF
        regs[OFFSET_TIMESTAMP_STOP_SESSION[0] + 1] = 0xFFFF
        for start, count, optional in LIVE_SEGMENTS:
            if start in self._unsupported_segments:
                continue
            try:
                values = self._read_registers(start, count)
            except UpdateFailed:
                if not optional:
                    raise
                fails = self._segment_failures.get(start, 0) + 1
                self._segment_failures[start] = fails
                _LOGGER.warning("Optionaler Registerbereich 0x%04X (%d) nicht lesbar (Versuch %d)", start, count, fails)
                if fails >= 3:
                    self._unsupported_segments.add(start)
                    _LOGGER.warning("Registerbereich 0x%04X wird ab jetzt übersprungen", start)
                continue
            self._segment_failures.pop(start, None)
            base = start - LIVE_BLOCK_START
            regs[base : base + count] = values
        return regs

    def _read_coils_individually(self) -> list[bool]:
        """Liest die Coils einzeln (wie die bewährte Alt-Integration); nicht lesbare Coils gelten als aus."""
        bits = [False] * COILS_BLOCK_COUNT
        for i in range(COILS_BLOCK_COUNT):
            addr = COILS_BLOCK_START + i
            if addr in self._unsupported_coils:
                continue
            try:
                self._ensure_connected()
                result = self.client.read_coils(addr, count=1, device_id=self.unit_id)
            except (OSError, ModbusException) as err:
                self._close()
                raise UpdateFailed(f"Verbindung zur Wallbox {self.host}:{self.port} unterbrochen: {err}") from err
            if result is None or result.isError():
                self._unsupported_coils.add(addr)
                _LOGGER.info("Coil 0x%04X nicht lesbar - wird übersprungen", addr)
                continue
            bits[i] = bool(result.bits[0])
        return bits

    def _read_coil_bits(self, address: int, count: int) -> list[bool]:
        """Liest Coils (mit Fehlerbehandlung wie bei den Registern)."""
        try:
            result = self.client.read_coils(address, count=count, device_id=self.unit_id)
        except (OSError, ModbusException) as err:
            self._close()
            raise UpdateFailed(f"Verbindung zur Wallbox {self.host}:{self.port} unterbrochen: {err}") from err
        if result is None or result.isError():
            raise UpdateFailed(f"Coil-Block konnte nicht gelesen werden ({self.host}:{self.port})")
        return list(result.bits[:count])

    # -- Setup -----------------------------------------------------------

    def read_device_info(self) -> None:
        """Liest den Geräteinfo-Block (Manufacturer/Product/Serial/Software) einmalig.

        Nicht kritisch: Schlägt das Lesen fehl, läuft die Integration ohne diese Texte
        weiter und versucht es beim nächsten Poll erneut.
        """
        try:
            regs = self._read_registers(DEVICE_INFO_BLOCK_START, DEVICE_INFO_BLOCK_COUNT)
        except UpdateFailed as err:
            _LOGGER.warning("Geräteinfo-Block konnte nicht gelesen werden: %s", err)
            return

        def _slice(offset_len: tuple[int, int]) -> list[int]:
            offset, length = offset_len
            return regs[offset : offset + length]

        self.device_info_data["manufacturer"] = _ascii_block_to_str(_slice(OFFSET_MANUFACTURER))
        self.device_info_data["product_reference"] = _ascii_block_to_str(_slice(OFFSET_PRODUCT_REFERENCE))
        self.device_info_data["serial_number"] = _ascii_block_to_str(_slice(OFFSET_SERIAL_NUMBER))
        self.device_info_data["software_version"] = _ascii_block_to_str(_slice(OFFSET_SOFTWARE_VERSION))

    # -- Polling -----------------------------------------------------------

    def _poll_sync(self) -> dict[str, Any]:
        """Liest den Live-Registerblock + Coil-Block in zwei Modbus-Aufrufen (synchron)."""
        regs = self._read_live_registers()
        bits = self._read_coils_individually()

        def reg(offset: int) -> int:
            return regs[offset]

        def signed(offset: int) -> int | None:
            raw = regs[offset]
            return None if raw == CURRENT_INVALID else _to_signed16(raw)

        def unsigned_or_none(offset: int) -> int | None:
            raw = regs[offset]
            return None if raw == VOLTAGE_POWER_INVALID else raw

        def uint32(offset_len: tuple[int, int]) -> int:
            offset, _ = offset_len
            return _to_uint32(regs[offset], regs[offset + 1])

        def ascii_str(offset_len: tuple[int, int]) -> str:
            offset, length = offset_len
            return _ascii_block_to_str(regs[offset : offset + length])

        def bit(offset: int) -> bool:
            return bool(bits[offset])

        data: dict[str, Any] = {
            "hw_current_limit_raw": reg(OFFSET_HW_CURRENT_LIMIT),
            "max_current_pp": reg(OFFSET_MAX_CURRENT_PP),
            "cp_state": ascii_str((OFFSET_CP_STATE, 1)),
            "pwm_value": reg(OFFSET_PWM_VALUE),
            "current_l1": None if signed(OFFSET_CURRENT_L1) is None else round(signed(OFFSET_CURRENT_L1) * 0.1, 2),
            "current_l2": None if signed(OFFSET_CURRENT_L2) is None else round(signed(OFFSET_CURRENT_L2) * 0.1, 2),
            "current_l3": None if signed(OFFSET_CURRENT_L3) is None else round(signed(OFFSET_CURRENT_L3) * 0.1, 2),
            "voltage_l1": None if unsigned_or_none(OFFSET_VOLTAGE_L1) is None else round(unsigned_or_none(OFFSET_VOLTAGE_L1) * 0.1, 1),
            "voltage_l2": None if unsigned_or_none(OFFSET_VOLTAGE_L2) is None else round(unsigned_or_none(OFFSET_VOLTAGE_L2) * 0.1, 1),
            "voltage_l3": None if unsigned_or_none(OFFSET_VOLTAGE_L3) is None else round(unsigned_or_none(OFFSET_VOLTAGE_L3) * 0.1, 1),
            "power_l1": unsigned_or_none(OFFSET_POWER_L1),
            "power_l2": unsigned_or_none(OFFSET_POWER_L2),
            "power_l3": unsigned_or_none(OFFSET_POWER_L3),
            "max_charging_current": reg(OFFSET_MAX_CHARGING_CURRENT),
            "led_mode": reg(OFFSET_LED_MODE),
            "access_control": reg(OFFSET_ACCESS_CONTROL),
            "error_code": reg(OFFSET_ERROR_CODE),
            "rfid_tag_uid": ascii_str(OFFSET_RFID_TAG_UID),
            "hardware_config": reg(OFFSET_HARDWARE_CONFIG),
            "led_intensity": reg(OFFSET_LED_INTENSITY),
            "energy_session": uint32(OFFSET_ENERGY_SESSION),
            "timestamp_start_session": uint32(OFFSET_TIMESTAMP_START_SESSION),
            "timestamp_stop_session": uint32(OFFSET_TIMESTAMP_STOP_SESSION),
            "session_state": reg(OFFSET_SESSION_STATE),
            "pulse_weight": reg(OFFSET_PULSE_WEIGHT),
            "timestamp_unix": uint32(OFFSET_TIMESTAMP_UNIX),
            # Coils
            "key_position": bit(COIL_OFFSET_KEY_POSITION),
            "station_available": bit(COIL_OFFSET_STATION_AVAILABLE),
            "station_available_fallback": bit(COIL_OFFSET_STATION_AVAILABLE_FALLBACK),
            "switch_3to1": bit(COIL_OFFSET_SWITCH_3TO1),
            "switch_3to1_fallback": bit(COIL_OFFSET_SWITCH_3TO1_FALLBACK),
            "proximity_short_press": bit(COIL_OFFSET_PROXIMITY_SHORT_PRESS),
            "lock_cable": bit(COIL_OFFSET_LOCK_CABLE),
            "rfid_reader_configured": bit(COIL_OFFSET_RFID_READER_CONFIGURED),
            "type_ef_occupied": bit(COIL_OFFSET_TYPE_EF_AVAILABILITY),
            "delay_fallback": bit(COIL_OFFSET_DELAY_FALLBACK),
            "rfid_auth_enabled": bit(COIL_OFFSET_RFID_AUTH_ENABLE),
            "ack_energy_session": bit(COIL_OFFSET_ACK_ENERGY_SESSION),
            "pulse_inconsistency": bit(COIL_OFFSET_PULSE_INCONSISTENCY),
            "datetime_not_set": bit(COIL_OFFSET_DATETIME_NOT_SET),
            "loop_generic_blink": bit(COIL_OFFSET_LOOP_GENERIC_BLINK),
        }
        self._derive_values(data)
        self._mask_unsupported(data)
        return data

    @staticmethod
    def _derive_values(data: dict[str, Any]) -> None:
        """Leitet Werte für Automationen/Energie-Dashboard aus den Rohdaten ab.

        - vehicle_connected: CP-Zustand A = kein Fahrzeug, B/C = Fahrzeug angeschlossen.
        - charging: CP-Zustand C2 und (falls Ströme bekannt) mindestens 0,5 A Gesamtstrom.
        - power_charging: gemessene Leistung, sonst Schätzung aus den Phasenströmen
          (mit gemessener Spannung, sonst 230 V je Phase). power_estimated zeigt, welcher Fall vorliegt.
        """
        cp = data.get("cp_state")
        data["vehicle_connected"] = None if not cp or cp[0] not in "ABCD" else cp[0] != "A"

        currents = [data.get(f"current_l{i}") for i in (1, 2, 3)]
        known_currents = [c for c in currents if c is not None]
        total_current = sum(max(c, 0.0) for c in known_currents)
        if cp is None:
            data["charging"] = None
        elif cp == "C2":
            data["charging"] = total_current >= 0.5 if known_currents else True
        else:
            data["charging"] = False

        measured = [data.get(f"power_l{i}") for i in (1, 2, 3)]
        known_power = [p for p in measured if p is not None]
        if known_power:
            data["power_charging"] = sum(known_power)
            data["power_estimated"] = False
        elif known_currents:
            estimate = 0.0
            for i in (1, 2, 3):
                current = data.get(f"current_l{i}")
                if current is None:
                    continue
                voltage = data.get(f"voltage_l{i}") or NOMINAL_VOLTAGE
                estimate += max(current, 0.0) * voltage
            data["power_charging"] = round(estimate)
            data["power_estimated"] = True
        else:
            data["power_charging"] = None
            data["power_estimated"] = None

    # Welche Daten-Schlüssel zu welchem optionalen Registerbereich gehören.
    _SEGMENT_KEYS = {
        0x0055: ("rfid_tag_uid",),
        0x0065: ("hardware_config",),
        0x0066: ("led_intensity",),
        0x0069: ("energy_session",),
        0x006B: ("timestamp_start_session", "timestamp_stop_session"),
        0x006F: ("session_state", "pulse_weight"),
        0x0071: ("timestamp_unix",),
    }
    _COIL_KEYS = (
        "key_position", "station_available", "station_available_fallback", "switch_3to1",
        "switch_3to1_fallback", "proximity_short_press", "lock_cable", "rfid_reader_configured",
        "type_ef_occupied", "delay_fallback", "rfid_auth_enabled", "ack_energy_session",
        "pulse_inconsistency", "datetime_not_set", "loop_generic_blink",
    )

    def _mask_unsupported(self, data: dict[str, Any]) -> None:
        """Setzt Werte nicht unterstützter Register/Coils auf None (statt eines erfundenen 0/False)."""
        for start, keys in self._SEGMENT_KEYS.items():
            if start in self._unsupported_segments or self._segment_failures.get(start):
                for key in keys:
                    data[key] = None
        for i, key in enumerate(self._COIL_KEYS):
            if (COILS_BLOCK_START + i) in self._unsupported_coils:
                data[key] = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Holt Live-Register- und Coil-Block von der Wallbox und synchronisiert bei Bedarf die Uhrzeit."""
        try:
            await self.hass.async_add_executor_job(self._ensure_connected)
        except (OSError, ModbusException) as err:
            self._close()
            raise UpdateFailed(f"Keine Verbindung zur Wallbox unter {self.host}:{self.port}: {err}") from err

        if not self.device_info_data:
            await self.hass.async_add_executor_job(self.read_device_info)
            if not self.client.connected:
                raise UpdateFailed(f"Verbindung zur Wallbox {self.host}:{self.port} wurde zurückgesetzt")

        data = await self.hass.async_add_executor_job(self._poll_sync)

        # Spec §3.3.31 / §3.4.12: Beendete Sessions (Session state = 2) müssen vom Client
        # quittiert werden, sonst bleiben sie im Session-Log der Wallbox (~20 Einträge).
        # Die Werte dieses Polls (Energie, Zeitstempel) sind bereits in `data` gesichert.
        if data.get("session_state") == 2:
            await self.hass.async_add_executor_job(self._write_coil_logged, COIL_ACK_ENERGY_SESSION, True)

        # Spec §3.4.6: Der Client MUSS die "Proximity short press"-Coil nach dem Lesen auf 0 zurücksetzen.
        if data.get("proximity_short_press"):
            await self.hass.async_add_executor_job(self._write_coil_logged, COIL_PROXIMITY_SHORT_PRESS, False)

        # Laut Spec (§3.4.14): Ist die Uhrzeit auf dem Board nicht gesetzt, wird das
        # Laden nach 10 Minuten gesperrt. Wir synchronisieren sie daher automatisch.
        if data.get("datetime_not_set"):
            await self.hass.async_add_executor_job(self._write_timestamp_now)

        return data

    # -- Schreibbefehle -----------------------------------------------------

    def _write_register_sync(self, address: int, value: int) -> str:
        """Schreibt ein Holding-Register und liest es zur Kontrolle zurück (synchron, im Executor).

        Ergebnis: "ok", "rejected" (Wallbox lehnt ab / keine Verbindung), "not_applied"
        (angenommen, aber Rücklesewert weicht ab) oder "no_readback" (Rücklesen nicht möglich).
        """
        try:
            result = self.client.write_register(address, value, device_id=self.unit_id)
            if result is None or result.isError():
                _LOGGER.warning("Register 0x%04X = %s: von der Wallbox abgelehnt (%s)", address, value, result)
                return "rejected"
            back = self.client.read_holding_registers(address, count=1, device_id=self.unit_id)
        except (OSError, ModbusException) as err:
            self._close()
            _LOGGER.warning("Register 0x%04X = %s: Verbindungsfehler (%s)", address, value, err)
            return "rejected"
        if back is None or back.isError():
            _LOGGER.info("Register 0x%04X = %s geschrieben, Rücklesen nicht möglich", address, value)
            return "no_readback"
        actual = back.registers[0]
        _LOGGER.info("Register 0x%04X geschrieben=%s, zurückgelesen=%s", address, value, actual)
        return "ok" if actual == value else "not_applied"

    def _write_coil_sync(self, address: int, value: bool) -> str:
        """Schreibt einen Coil und liest ihn zur Kontrolle zurück (Ergebnis wie bei _write_register_sync)."""
        try:
            result = self.client.write_coil(address, value, device_id=self.unit_id)
            if result is None or result.isError():
                _LOGGER.warning("Coil 0x%04X = %s: von der Wallbox abgelehnt (%s)", address, value, result)
                return "rejected"
            back = self.client.read_coils(address, count=1, device_id=self.unit_id)
        except (OSError, ModbusException) as err:
            self._close()
            _LOGGER.warning("Coil 0x%04X = %s: Verbindungsfehler (%s)", address, value, err)
            return "rejected"
        if back is None or back.isError() or not back.bits:
            _LOGGER.info("Coil 0x%04X = %s geschrieben, Rücklesen nicht möglich", address, value)
            return "no_readback"
        actual = bool(back.bits[0])
        _LOGGER.info("Coil 0x%04X geschrieben=%s, zurückgelesen=%s", address, value, actual)
        return "ok" if actual == bool(value) else "not_applied"

    @staticmethod
    def _check_write(outcome: str, what: str) -> None:
        """Wandelt ein fehlgeschlagenes Schreibergebnis in einen sichtbaren Fehler um."""
        if outcome == "rejected":
            raise HomeAssistantError(f"{what}: von der Wallbox abgelehnt")
        if outcome == "not_applied":
            raise HomeAssistantError(f"{what}: von der Wallbox angenommen, aber nicht übernommen (Rücklesewert weicht ab)")

    def _write_coil_logged(self, address: int, value: bool) -> None:
        """Schreibt einen Coil und loggt nur eine Warnung bei Fehler (für Hintergrund-Aktionen)."""
        outcome = self._write_coil_sync(address, value)
        if outcome in ("rejected", "not_applied"):
            _LOGGER.warning("Schreiben von Coil 0x%04X = %s fehlgeschlagen (%s)", address, value, outcome)

    def _write_timestamp_now(self) -> None:
        """Schreibt die aktuelle Unix-Zeit in das Timestamp-Register (2 Register, big-endian)."""
        now = int(time.time())
        high = (now >> 16) & 0xFFFF
        low = now & 0xFFFF
        try:
            result = self.client.write_registers(REG_TIMESTAMP_UNIX, [high, low], device_id=self.unit_id)
        except (OSError, ModbusException):
            self._close()
            _LOGGER.warning("Zeitstempel konnte nicht geschrieben werden (Verbindung unterbrochen)")
            return
        if result is None or result.isError():
            _LOGGER.warning("Zeitstempel konnte nicht auf die Wallbox geschrieben werden")

    async def async_write_max_current(self, current_a: int) -> None:
        """Setzt den maximalen Ladestrom in A (Register 0x0050, unskaliert)."""
        outcome = await self.hass.async_add_executor_job(
            self._write_register_sync, REG_MAX_CHARGING_CURRENT, int(current_a)
        )
        self._check_write(outcome, "Maximaler Ladestrom")
        await self.async_request_refresh()

    async def async_write_led_mode(self, mode_value: int) -> None:
        """Setzt den LED-Modus (Register 0x0052: 0=Witty Start, 1=Boost, 2=Solar; betrifft nur die HMI-LED)."""
        outcome = await self.hass.async_add_executor_job(self._write_register_sync, REG_LED_MODE, mode_value)
        self._check_write(outcome, "LED-Modus")
        await self.async_request_refresh()

    async def async_write_led_intensity(self, percent: int) -> None:
        """Setzt die LED-Helligkeit in % (Register 0x0066, 30-100)."""
        outcome = await self.hass.async_add_executor_job(self._write_register_sync, REG_LED_INTENSITY, int(percent))
        self._check_write(outcome, "LED-Helligkeit")
        await self.async_request_refresh()

    async def _async_write_coil(self, address: int, value: bool, error_text: str) -> None:
        """Hilfsfunktion zum Schreiben eines einzelnen Coils."""
        outcome = await self.hass.async_add_executor_job(self._write_coil_sync, address, value)
        self._check_write(outcome, error_text)
        await self.async_request_refresh()

    async def async_write_station_available(self, available: bool) -> None:
        """Setzt Coil 'Station available' (Verfügbarkeit / HMI-Sperre)."""
        await self._async_write_coil(
            COIL_STATION_AVAILABLE, available, "Ladestation verfügbar"
        )

    async def async_write_switch_3to1(self, single_phase: bool) -> None:
        """Setzt Coil 'Switch3to1' (Phasenumschaltung)."""
        await self._async_write_coil(
            COIL_SWITCH_3TO1, single_phase, "Phasenumschaltung (Nur 1 Phase laden)"
        )

    async def async_write_lock_cable(self, locked: bool) -> None:
        """Setzt Coil 'Lock cable' (Kabel dauerhaft verriegeln)."""
        await self._async_write_coil(
            COIL_LOCK_CABLE, locked, "Kabelverriegelung"
        )

    async def async_write_rfid_auth_enable(self, enabled: bool) -> None:
        """Setzt Coil 'Enable/Disable RFID Authentication'.

        Laut Spec lehnt der Server das Schreiben ab, solange auf irgendeiner
        Buchse eine Ladesession läuft.
        """
        await self._async_write_coil(
            COIL_RFID_AUTH_ENABLE,
            enabled,
            "RFID-Authentifizierung (läuft evtl. gerade eine Ladesession?)",
        )
