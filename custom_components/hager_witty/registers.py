"""Register map and (de)serialisation for the Hager WittyPlus Modbus TCP server.

This module is deliberately free of Home Assistant and pymodbus imports so that
it can be unit-tested on its own.

Source: "WittyPlus ModbusTCP server developer's Guide", version 1.0.1
(Hager group, October 2025).

IMPORTANT: the guide lists ALL addresses as HEXADECIMAL numbers (e.g. ``301E``),
therefore every address below is written as a ``0x...`` literal. Addresses are
used as-is (protocol address, no "-1" offset). Multi-register values use the
usual Modbus order (most significant word first).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final


class DataType(StrEnum):
    """Data types used by the Witty register map."""

    UINT16 = "uint16"
    INT16 = "int16"
    UINT32 = "uint32"
    INT32 = "int32"
    UINT64 = "uint64"
    STRING = "string"  # ASCII, 2 characters per register, NUL padded
    BYTES = "bytes"  # raw byte array
    VERSION = "version"  # 3 registers: major.minor.revision.build
    MAC = "mac"  # 3 registers: 6 bytes


# Fixed register count of the numeric types (checked by the tests).
NUMERIC_REGISTER_COUNT: Final[dict[DataType, int]] = {
    DataType.UINT16: 1,
    DataType.INT16: 1,
    DataType.UINT32: 2,
    DataType.INT32: 2,
    DataType.UINT64: 4,
}
SIGNED_TYPES: Final = frozenset({DataType.INT16, DataType.INT32})


@dataclass(frozen=True, slots=True, kw_only=True)
class Register:
    """One entry of the Witty register map."""

    key: str
    address: int
    count: int
    data_type: DataType
    scale: float = 1.0
    """Physical value = raw value * scale (e.g. 0.1 for "factor 0.1")."""
    invalid: int | None = None
    """Raw value the device uses for "measurement invalid"."""
    writable: bool = False
    min_raw: int = 0
    max_raw: int | None = None
    """Allowed raw range for writes (max defaults to the type maximum)."""


# ---------------------------------------------------------------------------
# Enumerations (register value -> language independent option key).
# The human readable texts live in translations/<language>.json.
# ---------------------------------------------------------------------------

# CP state (0x3008) is delivered as a 1-2 character string (DIN EN 61851).
CP_STATES: Final[tuple[str, ...]] = ("a1", "a2", "b1", "b2", "c1", "c2", "d1", "d2", "e", "f")
CP_STATES_VEHICLE_CONNECTED: Final = frozenset({"b1", "b2", "c1", "c2", "d1", "d2"})

# Wallbox status (0x302B, uint32)
STATUS_UNKNOWN_KEY: Final = "status_unknown"
WALLBOX_STATUS: Final[dict[int, str]] = {
    0x00000000: "no_error",
    0x00000100: "idle",
    0x00000101: "initialization",
    0x00000200: "wait_auth",
    0x00000201: "wait_ev_plug",
    0x00000202: "wait_ev_unplug",
    0x00000203: "wait_charging",
    0x00000204: "wait_ocpp_auth",
    0x00000205: "wait_modbus_tcp_auth",
    0x00000400: "wait_energy_off",
    0x00000401: "wait_energy_off_forced",
    0x00000402: "wait_energy_grid_load_shedding",
    0x00000403: "wait_energy_overheat",
    0x00000404: "wait_energy_smart_meter_tariff",
    0x00000405: "wait_energy_smart_meter_current",
    0x00000406: "wait_energy_smart_meter_lost",
    0x00000407: "wait_energy_input_forcing",
    0x00000408: "wait_energy_input_day_night",
    0x00000409: "wait_energy_hmi_lost",
    0x0000040A: "wait_energy_solar_reg",
    0x0000040B: "wait_energy_solar_eco",
    0x0000040C: "wait_energy_ocpp",
    0x0000040D: "wait_energy_modbus_tcp_normal",
    0x0000040E: "wait_energy_modbus_tcp_boost",
    0x0000040F: "wait_energy_modbus_tcp_solar",
    0x00000410: "wait_energy_modbus_tcp_lost",
    0x00000600: "charging_normal",
    0x00000601: "charging_slow",
    0x00000602: "charging_grid_load_shedding",
    0x00000603: "charging_smart_meter_lost",
    0x00000604: "charging_normal_forced",
    0x00000605: "charging_slow_forced",
    0x00000606: "charging_limited_hmi_lost",
    0x00000607: "charging_limited_option_board_default",
    0x00000608: "charging_solar",
    0x00000609: "charging_solar_eco",
    0x0000060A: "charging_forced_solar",
    0x0000060B: "charging_forced_solar_eco",
    0x0000060C: "charging_modbus_tcp_normal",
    0x0000060D: "charging_modbus_tcp_boost",
    0x0000060E: "charging_modbus_tcp_solar",
    0x0000060F: "charging_modbus_tcp_lost",
    0x00000800: "charge_finished",
    0x00001000: "ocpp_reservation",
    0xF0000000: "error_relay_4c_welded",
    0xF0000001: "error_relay_4c_broken",
    0xF0000002: "error_relay_4c_supply",
    0xF0000003: "error_rcd_broken",
    0xF0000004: "error_rotary_switch",
    0xF0000005: "error_socket_lock",
    0xF0000006: "error_socket_manual_unlock",
    0xF0000007: "error_socket_manual_lock",
    0xF0000008: "error_relay_l2_l3_welded",
    0xF0000009: "error_relay_l2_l3_broken",
    0xF000000A: "error_relay_l2_l3_supply",
    0xF0000200: "error_ev_rcd_6ma",
    0xF0000201: "error_ev_shunt_diode",
    0xF0000202: "error_ev_state_e",
    0xF0000203: "error_ev_ventilation",
    0xF0000204: "error_ev_simplified",
    0xF0000205: "error_ev_overload",
    0xF0000206: "error_ev_rcd_30ma_ac",
    0xF0000400: "error_cable",
    0xF0000500: "error_ocpp_inoperative",
    0xF0000600: "error_evse_energy_meter",
    0xF0000700: "error_modbus_tcp_inoperative",
    0xFFFFFFFF: STATUS_UNKNOWN_KEY,
}
STATUS_CHARGING_RANGE: Final = range(0x00000600, 0x00000610)
STATUS_ERROR_MIN: Final = 0xF0000000

# Session stop reason (0x5013)
STOP_REASONS: Final[dict[int, str]] = {
    0x00: "no_session",
    0x01: "session_running",
    0x02: "ev_unplug",
    0x03: "user_badge",
    0x04: "user_group_badge",
    0x05: "admin_badge",
    0x06: "power_lost",
    0x07: "reset_request",
    0x08: "watchdog",
    0x09: "assert",
    0x0A: "ocpp_remote_stop",
    0x0B: "ocpp_deauthorize",
    0x0C: "ocpp_parent_id",
    0x0D: "ocpp_unlock",
    0x0E: "ocpp_reset",
    0x0F: "modbus_tcp_availability",
    0x10: "ocpp_availability",
    0x20: "rotary_invalid_position",
    0x21: "lock_fail",
    0x22: "manual_unlock",
    0x23: "ev_6ma_error",
    0x24: "ev_state_e",
    0x25: "ev_simplified",
    0x26: "ev_ventilation",
    0x27: "ev_shunt_diode_error",
    0x28: "ev_overload",
    0x29: "cable_error",
    0x2A: "rcd_sensor_default",
    0x2B: "relay_4c_supply",
    0x2C: "relay_4c_welded",
    0x2D: "relay_4c_broken",
    0x2E: "multiple_same_option_board",
    0x2F: "energy_meter_error",
    0x30: "relay_l2_l3_supply",
    0x31: "relay_l2_l3_welded",
    0x32: "relay_l2_l3_broken",
    0x33: "ev_30ma_ac_error",
}

SESSION_STATES: Final[dict[int, str]] = {0: "no_session", 1: "running", 2: "ended"}
BADGE_TYPES: Final[dict[int, str]] = {0: "local", 1: "ocpp"}
LOCK_STATES: Final[dict[int, str]] = {
    0: "unlocked",
    1: "locked",
    2: "disabled_tethered",
    3: "blocked_unlocked",
    4: "blocked_locked",
}
PHASE_MODES: Final[dict[int, str]] = {0: "three_phase", 1: "single_phase"}
RFID_FEEDBACK: Final[dict[int, str]] = {
    0: "no_feedback",
    1: "authorized",
    2: "not_authorized",
    3: "discarded",
}

# ---------------------------------------------------------------------------
# Register definitions
# ---------------------------------------------------------------------------

_U16, _I16, _U32, _I32, _U64 = (
    DataType.UINT16,
    DataType.INT16,
    DataType.UINT32,
    DataType.INT32,
    DataType.UINT64,
)
_CURRENT_INVALID: Final = 0x7FFF  # guide: "if measure is invalid: 0x7FFFF" (int16 -> 0x7FFF)

REGISTERS: Final[tuple[Register, ...]] = (
    # --- Device information (read once at setup) -------------------------
    Register(key="modbus_version", address=0x1001, count=1, data_type=_U16),
    Register(key="product_reference", address=0x1003, count=16, data_type=DataType.STRING),
    Register(key="wallbox_id", address=0x1013, count=16, data_type=DataType.STRING),
    Register(key="software_version", address=0x1023, count=3, data_type=DataType.VERSION),
    # --- Network (read once at setup) -------------------------------------
    Register(key="mac_address", address=0x2000, count=3, data_type=DataType.MAC),
    # --- Clock -------------------------------------------------------------
    Register(
        key="wallbox_time",
        address=0x3000,
        count=4,
        data_type=_U64,
        writable=True,
        max_raw=2**64 - 1,
    ),
    # --- Charging session: measurements ------------------------------------
    Register(key="time_set", address=0x3005, count=1, data_type=_U16),
    Register(key="hw_current_limit", address=0x3006, count=1, data_type=_U16),
    Register(key="cable_current_limit", address=0x3007, count=1, data_type=_U16),
    Register(key="cp_state", address=0x3008, count=1, data_type=DataType.STRING),
    Register(key="pwm_duty", address=0x3009, count=1, data_type=_U16),
    Register(key="current_l1", address=0x300A, count=1, data_type=_I16, scale=0.1, invalid=_CURRENT_INVALID),
    Register(key="current_l2", address=0x300B, count=1, data_type=_I16, scale=0.1, invalid=_CURRENT_INVALID),
    Register(key="current_l3", address=0x300C, count=1, data_type=_I16, scale=0.1, invalid=_CURRENT_INVALID),
    Register(key="voltage_l1", address=0x300D, count=1, data_type=_U16, scale=0.1),
    Register(key="voltage_l2", address=0x300E, count=1, data_type=_U16, scale=0.1),
    Register(key="voltage_l3", address=0x300F, count=1, data_type=_U16, scale=0.1),
    Register(key="power_l1", address=0x3010, count=1, data_type=_I16),
    Register(key="power_l2", address=0x3011, count=1, data_type=_I16),
    Register(key="power_l3", address=0x3012, count=1, data_type=_I16),
    Register(key="power_total", address=0x3013, count=2, data_type=_I32),
    # --- Charging session: control (R/W) -----------------------------------
    Register(
        key="max_current",
        address=0x301E,
        count=1,
        data_type=_U16,
        scale=0.1,
        writable=True,
        max_raw=320,
    ),
    Register(
        key="max_current_fallback",
        address=0x301F,
        count=1,
        data_type=_U16,
        scale=0.1,
        writable=True,
        max_raw=320,
    ),
    Register(key="evcs_available", address=0x3020, count=1, data_type=_U16, writable=True, max_raw=1),
    Register(key="evcs_available_fallback", address=0x3021, count=1, data_type=_U16, writable=True, max_raw=1),
    Register(key="phase_mode", address=0x3022, count=1, data_type=_U16, writable=True, max_raw=1),
    Register(key="phase_mode_fallback", address=0x3023, count=1, data_type=_U16, writable=True, max_raw=1),
    Register(key="lock_state", address=0x3025, count=1, data_type=_U16),
    Register(key="fallback_delay", address=0x3026, count=1, data_type=_U16, writable=True, max_raw=1),
    Register(key="status", address=0x302B, count=2, data_type=_U32),
    # --- RFID (only meaningful with RFID authentication enabled) -----------
    Register(key="rfid_uid_size", address=0x4001, count=1, data_type=_U16),
    Register(key="rfid_uid_raw", address=0x4002, count=5, data_type=DataType.BYTES),
    Register(key="rfid_feedback", address=0x400B, count=1, data_type=_U16, writable=True, max_raw=3),
    # --- Energy / session ---------------------------------------------------
    Register(key="session_energy", address=0x5000, count=2, data_type=_U32),
    Register(key="session_start", address=0x5002, count=4, data_type=_U64),
    Register(key="session_stop", address=0x5006, count=4, data_type=_U64),
    Register(key="charge_duration", address=0x500A, count=2, data_type=_U32),
    Register(key="session_badge_size", address=0x500C, count=1, data_type=_U16),
    Register(key="session_badge_raw", address=0x500D, count=5, data_type=DataType.BYTES),
    Register(key="badge_type", address=0x5012, count=1, data_type=_U16),
    Register(key="stop_reason", address=0x5013, count=1, data_type=_U16),
    Register(key="session_state", address=0x5014, count=1, data_type=_U16),
)
REGISTER_BY_KEY: Final[dict[str, Register]] = {reg.key: reg for reg in REGISTERS}


@dataclass(frozen=True, slots=True)
class Block:
    """A contiguous range of documented registers that is read with ONE request.

    Blocks must never span an undocumented gap: an unknown address may make the
    whole request fail with an "illegal data address" exception.
    """

    name: str
    start: int
    count: int
    registers: tuple[Register, ...]
    optional: bool = False
    """Optional blocks may be rejected by the device (e.g. RFID registers while
    RFID authentication is off). A rejection is not an error; the block is
    retried only every few minutes."""


def _block(name: str, start: int, count: int, *, optional: bool = False) -> Block:
    end = start + count
    regs = tuple(r for r in REGISTERS if start <= r.address and r.address + r.count <= end)
    return Block(name=name, start=start, count=count, registers=regs, optional=optional)


# Polled on every update.
POLL_BLOCKS: Final[tuple[Block, ...]] = (
    _block("measurements", 0x3005, 16),  # 0x3005 ... 0x3014
    _block("control", 0x301E, 6),  # 0x301E ... 0x3023
    _block("lock", 0x3025, 2),  # 0x3025 ... 0x3026
    _block("status", 0x302B, 2),
    _block("clock", 0x3000, 4),
    _block("session", 0x5000, 21),  # 0x5000 ... 0x5014
    _block("rfid", 0x4001, 6, optional=True),  # 0x4001 ... 0x4006
    _block("rfid_feedback", 0x400B, 1, optional=True),
)

# Read once when the integration is set up.
INFO_CORE_BLOCK: Final = _block("info_core", 0x1003, 35)  # 0x1003 ... 0x1025
INFO_OPTIONAL_BLOCKS: Final[tuple[Block, ...]] = (
    _block("info_modbus", 0x1001, 1, optional=True),
    _block("info_network", 0x2000, 3, optional=True),
)
ALL_BLOCKS: Final[tuple[Block, ...]] = (*POLL_BLOCKS, INFO_CORE_BLOCK, *INFO_OPTIONAL_BLOCKS)


# ---------------------------------------------------------------------------
# Decoding / encoding
# ---------------------------------------------------------------------------


def _combine(words: Sequence[int]) -> int:
    value = 0
    for word in words:
        value = (value << 16) | (word & 0xFFFF)
    return value


def _to_signed(value: int, bits: int) -> int:
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def _words_to_bytes(words: Sequence[int]) -> bytes:
    out = bytearray()
    for word in words:
        out += (word & 0xFFFF).to_bytes(2, "big")
    return bytes(out)


def decode_register(reg: Register, words: Sequence[int]) -> Any:
    """Convert the raw register words of ``reg`` into a Python value.

    Returns ``None`` if the device flags the value as invalid.
    """
    if len(words) != reg.count:
        raise ValueError(f"{reg.key}: expected {reg.count} words, got {len(words)}")

    data_type = reg.data_type
    if data_type is DataType.STRING:
        text = _words_to_bytes(words).split(b"\x00", 1)[0].decode("ascii", errors="ignore").strip()
        return text or None
    if data_type is DataType.BYTES:
        return _words_to_bytes(words)
    if data_type is DataType.MAC:
        return ":".join(f"{byte:02X}" for byte in _words_to_bytes(words))
    if data_type is DataType.VERSION:
        # register[0] = major/minor, register[1] = revision/build(high),
        # register[2] = build(low)/0   -> e.g. 255.255.255.65535
        major, minor = words[0] >> 8, words[0] & 0xFF
        revision = words[1] >> 8
        build = ((words[1] & 0xFF) << 8) | (words[2] >> 8)
        return f"{major}.{minor}.{revision}.{build}"

    raw = _combine(words)
    if data_type in SIGNED_TYPES:
        raw = _to_signed(raw, 16 * reg.count)
    if reg.invalid is not None and raw == reg.invalid:
        return None
    if reg.scale != 1.0:
        return round(raw * reg.scale, 6)
    return raw


def decode_block(block: Block, words: Sequence[int]) -> dict[str, Any]:
    """Decode all registers of ``block`` from the words returned by the device."""
    if len(words) < block.count:
        raise ValueError(f"{block.name}: expected {block.count} words, got {len(words)}")
    result: dict[str, Any] = {}
    for reg in block.registers:
        offset = reg.address - block.start
        result[reg.key] = decode_register(reg, words[offset : offset + reg.count])
    return result


def encode_value(reg: Register, value: float) -> list[int]:
    """Convert a physical value into the register words to write."""
    if not reg.writable:
        raise ValueError(f"Register {reg.key} is read-only")
    if reg.data_type not in NUMERIC_REGISTER_COUNT:
        raise ValueError(f"Register {reg.key} is not numeric")

    raw = round(value / reg.scale) if reg.scale != 1.0 else round(value)
    bits = 16 * reg.count
    maximum = reg.max_raw if reg.max_raw is not None else (1 << bits) - 1
    if not reg.min_raw <= raw <= maximum:
        raise ValueError(f"{reg.key}: {value} is outside the allowed range")
    return [(raw >> (16 * (reg.count - 1 - i))) & 0xFFFF for i in range(reg.count)]


# ---------------------------------------------------------------------------
# Derived values
# ---------------------------------------------------------------------------

_VALID_UID_SIZES: Final = (4, 7, 10)


def _uid_hex(raw: bytes | None, size: int | None) -> str | None:
    """RFID UID as upper-case hex string, ``None`` if no tag / invalid size."""
    if raw is None or size not in _VALID_UID_SIZES:
        return None
    chunk = raw[:size]
    if not any(chunk):
        return None
    return chunk.hex().upper()


def status_to_key(code: int | None) -> str | None:
    """Option key of a wallbox status code (``None`` for unknown codes)."""
    return None if code is None else WALLBOX_STATUS.get(code)


def is_charging_status(code: int) -> bool:
    """True for the ``CHARGING_*`` status codes (0x600 ... 0x60F)."""
    return code in STATUS_CHARGING_RANGE


def is_error_status(code: int) -> bool:
    """True for the ``ERROR_*`` status codes (0xF0000000 ...)."""
    return code >= STATUS_ERROR_MIN and code != 0xFFFFFFFF


def derive_values(data: Mapping[str, Any]) -> dict[str, Any]:
    """Compute values that are derived from several registers.

    Keys are only added if all inputs are available, so a missing register block
    results in an unavailable entity instead of a wrong value.
    """
    derived: dict[str, Any] = {}

    if data.get("session_badge_size") is not None:
        derived["session_badge"] = _uid_hex(data.get("session_badge_raw"), data["session_badge_size"])
    if data.get("rfid_uid_size") is not None:
        derived["rfid_tag"] = _uid_hex(data.get("rfid_uid_raw"), data["rfid_uid_size"])

    status = data.get("status")
    if status is not None:
        derived["charging"] = is_charging_status(status)
        derived["error"] = is_error_status(status)

    cp_state = data.get("cp_state")
    if cp_state is not None:
        derived["vehicle_connected"] = cp_state.lower() in CP_STATES_VEHICLE_CONNECTED
    return derived
