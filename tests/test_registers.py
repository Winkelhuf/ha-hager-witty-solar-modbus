"""Tests für die Register-Tabelle (ohne laufendes Home Assistant)."""

from __future__ import annotations

import pytest

from custom_components.hager_witty import registers as r


def test_addresses_match_the_developers_guide() -> None:
    """Stichprobe: Adressen sind HEX-Werte aus der Herstellertabelle."""
    expected = {
        "max_current": 0x301E,
        "phase_mode": 0x3022,
        "status": 0x302B,
        "power_total": 0x3013,
        "session_energy": 0x5000,
        "session_state": 0x5014,
        "stop_reason": 0x5013,
        "rfid_feedback": 0x400B,
    }
    for key, address in expected.items():
        assert r.REGISTER_BY_KEY[key].address == address, key


def test_registers_do_not_overlap() -> None:
    """Kein Adressbereich wird doppelt belegt."""
    used: dict[int, str] = {}
    for reg in r.REGISTERS:
        for address in range(reg.address, reg.address + reg.count):
            assert address not in used, f"{reg.key} überlappt mit {used[address]}"
            used[address] = reg.key


def test_numeric_register_counts_match_type() -> None:
    """uint32 belegt 2, uint64 4 Register usw."""
    for reg in r.REGISTERS:
        if reg.data_type in r.NUMERIC_REGISTER_COUNT:
            assert reg.count == r.NUMERIC_REGISTER_COUNT[reg.data_type], reg.key


def test_blocks_have_no_gaps_and_cover_every_register() -> None:
    """Ein Block darf keine undokumentierte Adresse enthalten und jedes Register liegt in einem Block."""
    for block in r.ALL_BLOCKS:
        covered = sorted(a for reg in block.registers for a in range(reg.address, reg.address + reg.count))
        assert covered == list(range(block.start, block.start + block.count)), block.name
    in_blocks = {reg.key for block in r.ALL_BLOCKS for reg in block.registers}
    assert in_blocks == {reg.key for reg in r.REGISTERS}


def test_modbus_request_limit() -> None:
    """Modbus erlaubt höchstens 125 Register pro Leseanfrage."""
    assert all(block.count <= 125 for block in r.ALL_BLOCKS)


def test_decode_scaled_and_invalid_currents() -> None:
    """Faktor 0,1 A und der Wert 0x7FFF = ungültige Messung."""
    current = r.REGISTER_BY_KEY["current_l1"]
    assert r.decode_register(current, [165]) == 16.5
    assert r.decode_register(current, [0x7FFF]) is None
    assert r.decode_register(current, [0xFFFF]) == -0.1


def test_decode_signed_32bit_power() -> None:
    """Global Power ist int32 (Hauptwort zuerst)."""
    power = r.REGISTER_BY_KEY["power_total"]
    assert r.decode_register(power, [0x0001, 0x86A0]) == 100_000
    assert r.decode_register(power, [0xFFFF, 0xFFF6]) == -10


def test_decode_strings_version_mac() -> None:
    """Texte, Softwareversion und MAC-Adresse."""
    assert r.decode_register(r.REGISTER_BY_KEY["cp_state"], [0x4231]) == "B1"
    assert r.decode_register(r.REGISTER_BY_KEY["cp_state"], [0x0000]) is None
    version = r.REGISTER_BY_KEY["software_version"]
    assert r.decode_register(version, [0xFFFF, 0xFFFF, 0xFF00]) == "255.255.255.65535"
    assert r.decode_register(version, [0x0102, 0x0300, 0x0100]) == "1.2.3.1"
    assert r.decode_register(r.REGISTER_BY_KEY["mac_address"], [0x0011, 0x2233, 0x4455]) == "00:11:22:33:44:55"


def test_decode_uint64_timestamp() -> None:
    """Unix-Zeit besteht aus vier Registern."""
    assert r.decode_register(r.REGISTER_BY_KEY["session_start"], [0, 0, 0x6500, 0x0000]) == 0x65000000


def test_decode_block_uses_offsets() -> None:
    """decode_block schneidet jedes Register an der richtigen Stelle heraus."""
    block = r.POLL_BLOCKS[1]  # control: 0x301E ... 0x3023
    values = r.decode_block(block, [160, 100, 1, 0, 1, 0])
    assert values["max_current"] == 16.0
    assert values["max_current_fallback"] == 10.0
    assert values["evcs_available"] == 1
    assert values["phase_mode"] == 1


def test_encode_value() -> None:
    """Physikalischer Wert -> Registerwort."""
    assert r.encode_value(r.REGISTER_BY_KEY["max_current"], 16.0) == [160]
    assert r.encode_value(r.REGISTER_BY_KEY["max_current"], 6.0) == [60]
    assert r.encode_value(r.REGISTER_BY_KEY["phase_mode"], 1) == [1]
    assert r.encode_value(r.REGISTER_BY_KEY["wallbox_time"], 1_790_000_000) == [0, 0, 27313, 15232]


@pytest.mark.parametrize(("key", "value"), [("max_current", 32.1), ("max_current", -0.1), ("phase_mode", 2)])
def test_encode_rejects_out_of_range(key: str, value: float) -> None:
    """Werte außerhalb des Bereichs werden nicht geschrieben."""
    with pytest.raises(ValueError, match="outside"):
        r.encode_value(r.REGISTER_BY_KEY[key], value)


def test_encode_rejects_read_only_register() -> None:
    """Nur R/W-Register dürfen beschrieben werden."""
    with pytest.raises(ValueError, match="read-only"):
        r.encode_value(r.REGISTER_BY_KEY["power_total"], 1)


def test_derived_values() -> None:
    """Abgeleitete Werte: lädt / Fahrzeug verbunden / Fehler / Badge."""
    derived = r.derive_values(
        {
            "status": 0x603,
            "cp_state": "C2",
            "session_badge_size": 4,
            "session_badge_raw": bytes([0xDE, 0xAD, 0xBE, 0xEF, 0, 0, 0, 0, 0, 0]),
            "rfid_uid_size": 4,
            "rfid_uid_raw": bytes(10),
        }
    )
    assert derived == {
        "session_badge": "DEADBEEF",
        "rfid_tag": None,
        "charging": True,
        "error": False,
        "vehicle_connected": True,
    }
    assert r.derive_values({"status": 0xF0000005})["error"] is True
    assert r.derive_values({"status": 0xFFFFFFFF})["error"] is False
    assert r.derive_values({"status": 0x100})["charging"] is False
    assert "charging" not in r.derive_values({})


def test_enum_keys_are_valid_translation_keys() -> None:
    """Optionsschlüssel müssen die hassfest-Regeln für Übersetzungsschlüssel erfüllen."""
    import re

    key_re = re.compile(r"^(?!.+[_-]{2})(?![_-])[a-z0-9-_]+(?<![_-])$")
    for mapping in (
        r.WALLBOX_STATUS,
        r.STOP_REASONS,
        r.SESSION_STATES,
        r.BADGE_TYPES,
        r.LOCK_STATES,
        r.PHASE_MODES,
        r.RFID_FEEDBACK,
    ):
        values = list(mapping.values())
        assert len(values) == len(set(values))
        assert all(key_re.match(v) for v in values)
