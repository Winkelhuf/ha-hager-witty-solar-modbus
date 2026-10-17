"""Modbus-Register des generischen Hager EVCS-Kommunikationsboards (B1280).

Gilt laut Spezifikation "EVCS_Modbus_v0.28" für die Witty-Familie (u.a. Witty
Solar), die dieses Board verwendet. Adressen sind die 0-basierten Modbus-
Protokolladressen aus der "Address"-Spalte der Spec (nicht die 1-basierte
"Register number"-Spalte, die nur der Dokumentation dient).

Anders als die WittyPlus-eigene ModbusTCP-Schnittstelle kennt dieses Board
sowohl Holding Register (FC 03/06/16) als auch Coils (FC 01/05/15).
"""
from __future__ import annotations

REG_MAGICBYTE = 0x0000  # Konstanter Wert 0xE3DC, geeignet für einen Verbindungstest
MAGICBYTE_VALUE = 0xE3DC
REG_MODBUS_VERSION = 0x0001

# --- Geräteinformationen: ein Block, einmalig beim Setup gelesen -----------
# Register 4-67 (0x0003-0x0042), 64 Register am Stück: Manufacturer,
# Product Reference, Serial Number, Software version (je 16 Register String).
DEVICE_INFO_BLOCK_START = 0x0003
DEVICE_INFO_BLOCK_COUNT = 64

OFFSET_MANUFACTURER = (0, 16)
OFFSET_PRODUCT_REFERENCE = (16, 16)
OFFSET_SERIAL_NUMBER = (32, 16)
OFFSET_SOFTWARE_VERSION = (48, 16)

# --- Live-Block: ein zusammenhängender Block, der bei jedem Poll gelesen wird
# Register 68-115 (0x0043-0x0072), 48 Register am Stück.
LIVE_BLOCK_START = 0x0043
LIVE_BLOCK_COUNT = 48

OFFSET_HW_CURRENT_LIMIT = 0
OFFSET_MAX_CURRENT_PP = 1
OFFSET_CP_STATE = 2
OFFSET_PWM_VALUE = 3
OFFSET_CURRENT_L1 = 4
OFFSET_CURRENT_L2 = 5
OFFSET_CURRENT_L3 = 6
OFFSET_VOLTAGE_L1 = 7
OFFSET_VOLTAGE_L2 = 8
OFFSET_VOLTAGE_L3 = 9
OFFSET_POWER_L1 = 10
OFFSET_POWER_L2 = 11
OFFSET_POWER_L3 = 12
OFFSET_MAX_CHARGING_CURRENT = 13
OFFSET_MAX_CHARGING_CURRENT_FALLBACK = 14
OFFSET_LED_MODE = 15
OFFSET_ACCESS_CONTROL = 16
OFFSET_ERROR_CODE = 17
OFFSET_RFID_TAG_UID = (18, 16)
OFFSET_HARDWARE_CONFIG = 34
OFFSET_LED_INTENSITY = 35
OFFSET_FEEDBACK_RFID = 36
OFFSET_GENERIC_BLINK_COLOR = 37
OFFSET_ENERGY_SESSION = (38, 2)
OFFSET_TIMESTAMP_START_SESSION = (40, 2)
OFFSET_TIMESTAMP_STOP_SESSION = (42, 2)
OFFSET_SESSION_STATE = 44
OFFSET_PULSE_WEIGHT = 45
OFFSET_TIMESTAMP_UNIX = (46, 2)

# Absolute Adresse, falls einzeln geschrieben werden muss (Maximum Charging
# Current, LED mode, LED Intensity, Timestamp Unix).
REG_MAX_CHARGING_CURRENT = 0x0050
REG_LED_MODE = 0x0052
REG_LED_INTENSITY = 0x0066
REG_TIMESTAMP_UNIX = 0x0071

# --- Coils: ein Block, der bei jedem Poll gelesen wird ----------------------
# Coils 1-15 (Adresse 0x0000-0x000E), 15 Coils am Stück.
COILS_BLOCK_START = 0x0000
COILS_BLOCK_COUNT = 15

COIL_OFFSET_KEY_POSITION = 0
COIL_OFFSET_STATION_AVAILABLE = 1
COIL_OFFSET_STATION_AVAILABLE_FALLBACK = 2
COIL_OFFSET_SWITCH_3TO1 = 3
COIL_OFFSET_SWITCH_3TO1_FALLBACK = 4
COIL_OFFSET_PROXIMITY_SHORT_PRESS = 5
COIL_OFFSET_LOCK_CABLE = 6
COIL_OFFSET_RFID_READER_CONFIGURED = 7
COIL_OFFSET_TYPE_EF_AVAILABILITY = 8
COIL_OFFSET_DELAY_FALLBACK = 9
COIL_OFFSET_RFID_AUTH_ENABLE = 10
COIL_OFFSET_ACK_ENERGY_SESSION = 11
COIL_OFFSET_PULSE_INCONSISTENCY = 12
COIL_OFFSET_DATETIME_NOT_SET = 13
COIL_OFFSET_LOOP_GENERIC_BLINK = 14

# Absolute Coil-Adressen, falls einzeln geschrieben werden muss.
COIL_STATION_AVAILABLE = 0x0001
COIL_PROXIMITY_SHORT_PRESS = 0x0005
COIL_ACK_ENERGY_SESSION = 0x000B
COIL_SWITCH_3TO1 = 0x0003
COIL_LOCK_CABLE = 0x0006
COIL_RFID_AUTH_ENABLE = 0x000A

# --- Invalid-/Default-Marker laut Spec --------------------------------------
CURRENT_INVALID = 0x7FFF  # Int16
VOLTAGE_POWER_INVALID = 0xFFFF  # UInt16

# --- Decode-Tabellen ---------------------------------------------------------
CP_STATES = ("A1", "A2", "B1", "B2", "C1", "C2", "E", "F")
# Sensor-Optionen in Kleinbuchstaben (Voraussetzung für übersetzbare Zustandstexte).
CP_STATE_OPTIONS = tuple(state.lower() for state in CP_STATES)

HARDWARE_CURRENT_LIMIT_MAP = {1: 10, 2: 13, 3: 16, 4: 20, 5: 25, 6: 32}


def hardware_limit_amps(raw: int | None) -> int | None:
    """Hardware-Stromlimit in A. Spec-Enum 1..6; ältere Firmware liefert direkt Ampere (z. B. 32)."""
    if raw is None:
        return None
    raw = int(raw)
    if raw in HARDWARE_CURRENT_LIMIT_MAP:
        return HARDWARE_CURRENT_LIMIT_MAP[raw]
    return raw if 6 <= raw <= 80 else None

ACCESS_CONTROL_MAP = {0: "standalone", 3: "key_switch"}

ERROR_CODE_MAP = {
    0: "no_error",
    1: "cable_failure",
    2: "cp_short_circuit_failure",
    3: "car_overconsumption",
    4: "ventilation_error",
    6: "cp_failure",
    9: "rcd_6ma_detection",
    128: "rfid_reader_error",
    129: "fatal_error_current_selector",
    130: "fatal_error_welded_contact_1",
    133: "fatal_error_dc_sensor_6ma",
    134: "neutral_breakage",
}

HARDWARE_CONFIG_MAP = {
    0: "domestic_plug_and_keyswitch",
    1: "keyswitch",
    2: "domestic_plug",
    3: "none",
}

# Register 0x0052 "Boost/Solar mode": laut Spec (§3.3.23) ändert es AUSSCHLIESSLICH das
# LED-/HMI-Verhalten, nicht die Ladeleistung.
LED_MODE_MAP = {0: "witty_start", 1: "boost", 2: "solar"}
LED_MODE_MAP_REVERSE = {v: k for k, v in LED_MODE_MAP.items()}

SESSION_STATE_MAP = {0: "no_session", 1: "running", 2: "ended"}

PULSE_WEIGHT_MAP = {
    0: "estimated_no_meter",
    1: "ecp140d_single_phase",
    5: "ecp380d_three_phase",
    10: "saia_aae3",
}
