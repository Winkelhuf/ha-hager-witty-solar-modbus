"""
Konsistenz-Tests für Manifest und Übersetzungen der Witty-Solar-Wallbox-Integration.

Sie laufen ohne laufendes Home Assistant und schlagen fehl, wenn
- die Domain in manifest.json nicht zum Ordnernamen passt,
- strings.json und translations/en.json auseinanderlaufen,
- eine Sprache Schlüssel gegenüber Englisch verliert oder gewinnt,
- ein Sensor/Binary-Sensor/Number/Switch/Select im Code keinen Namen in den
  Übersetzungen hat (oder umgekehrt eine Übersetzung keinen Code-Gegenpart),
- ein ENUM-Sensor Zustände anbietet, für die keine Übersetzung existiert.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

COMPONENT = Path(__file__).parent.parent / "custom_components" / "witty_solar_wallbox"
TRANSLATIONS = COMPONENT / "translations"

LANGUAGE_FILES = sorted(TRANSLATIONS.glob("*.json"))


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _flatten(data: dict, prefix: str = "") -> dict[str, str]:
    flat: dict[str, str] = {}
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(_flatten(value, path))
        else:
            flat[path] = value
    return flat


STRINGS = _load(COMPONENT / "strings.json")
STRINGS_FLAT = _flatten(STRINGS)

KEY_RE = re.compile(r"^[a-z0-9_]+$")


def test_manifest_domain_matches_folder_name() -> None:
    """Die Domain in manifest.json muss dem Ordnernamen entsprechen (hassfest-Pflicht)."""
    manifest = _load(COMPONENT / "manifest.json")
    assert manifest["domain"] == COMPONENT.name


def test_manifest_has_required_fields() -> None:
    """Minimalfelder, die hassfest und HACS erwarten."""
    manifest = _load(COMPONENT / "manifest.json")
    for field in ("domain", "name", "codeowners", "config_flow", "documentation", "issue_tracker", "requirements", "version"):
        assert field in manifest, f"manifest.json: Feld '{field}' fehlt"
    assert manifest["codeowners"], "manifest.json: mindestens ein Codeowner erforderlich"


def test_strings_json_is_the_english_source() -> None:
    """strings.json und translations/en.json müssen identisch sein."""
    en = _load(TRANSLATIONS / "en.json")
    assert STRINGS == en


@pytest.mark.parametrize("path", LANGUAGE_FILES, ids=lambda p: p.stem)
def test_language_has_exactly_the_english_keys(path: Path) -> None:
    """Keine fehlenden und keine überzähligen Schlüssel gegenüber strings.json (= en.json)."""
    flat = _flatten(_load(path))

    assert not set(STRINGS_FLAT) - set(flat), f"fehlt in {path.name}: {sorted(set(STRINGS_FLAT) - set(flat))}"
    assert not set(flat) - set(STRINGS_FLAT), f"überzählig in {path.name}: {sorted(set(flat) - set(STRINGS_FLAT))}"


@pytest.mark.parametrize("path", [COMPONENT / "strings.json", *LANGUAGE_FILES], ids=lambda p: p.stem)
def test_no_empty_texts(path: Path) -> None:
    """Leere Texte würden in Home Assistant nur den rohen Entity-Key anzeigen."""
    for key, text in _flatten(_load(path)).items():
        assert text.strip(), f"{path.name}: {key} ist leer"


def _entity_keys_from_source(fname: str) -> set[str]:
    """Extrahiert alle key="..."-Vorkommen aus einer Plattformdatei (robust ohne HA-Import)."""
    src = (COMPONENT / fname).read_text(encoding="utf-8")
    # Negative Lookbehind: "translation_key=..." (z. B. in Exceptions) soll nicht als Entity-Key zählen.
    return set(re.findall(r'(?<![A-Za-z_])key="([a-z0-9_]+)"', src))


PLATFORM_FILES = {
    "sensor": "sensor.py",
    "binary_sensor": "binary_sensor.py",
    "number": "number.py",
    "switch": "switch.py",
    "select": "select.py",
}


@pytest.mark.parametrize("platform", sorted(PLATFORM_FILES), ids=lambda p: p)
def test_every_entity_in_code_has_a_translation(platform: str) -> None:
    """Jeder Entity-Key im Code hat einen Namen in den Übersetzungen - und umgekehrt."""
    code_keys = _entity_keys_from_source(PLATFORM_FILES[platform])
    translated = set(STRINGS["entity"].get(platform, {}).keys())

    missing = code_keys - translated
    orphan = translated - code_keys
    assert not missing, f"Name fehlt für {platform}: {sorted(missing)}"
    assert not orphan, f"Übersetzung ohne Entity im Code ({platform}): {sorted(orphan)}"


def test_translation_keys_are_valid_ha_keys() -> None:
    """translation_key darf nur Kleinbuchstaben, Ziffern und Unterstriche enthalten."""
    for platform in PLATFORM_FILES:
        for key in STRINGS["entity"].get(platform, {}):
            assert KEY_RE.match(key), f"ungültiger translation_key in {platform}: {key}"


def test_poll_register_offsets_do_not_collide() -> None:
    """Die Offsets im Live-Registerblock dürfen sich nicht überschneiden."""
    from custom_components.witty_solar_wallbox import registers as regs

    # Alle numerischen OFFSET_*-Konstanten (einzelne Register, keine Tupel) einsammeln.
    single_offsets = []
    for name in dir(regs):
        if not name.startswith("OFFSET_"):
            continue
        value = getattr(regs, name)
        if isinstance(value, int):
            single_offsets.append((name, value))

    seen: dict[int, str] = {}
    for name, offset in single_offsets:
        assert offset not in seen, f"Offset {offset} doppelt belegt: {seen[offset]} und {name}"
        seen[offset] = name


def test_led_mode_map_is_consistent() -> None:
    """Die LED-Modus-Map (Register 0x0052) muss bijektiv sein (für die Select-Entity)."""
    from custom_components.witty_solar_wallbox.registers import (
        LED_MODE_MAP,
        LED_MODE_MAP_REVERSE,
    )

    assert len(LED_MODE_MAP) == len(LED_MODE_MAP_REVERSE)
    for value, name in LED_MODE_MAP.items():
        assert LED_MODE_MAP_REVERSE[name] == value


def test_select_options_match_registers() -> None:
    """Die Optionen der LED-Modus-Select-Entity müssen zur Registerkarte passen."""
    from custom_components.witty_solar_wallbox.registers import LED_MODE_MAP
    from custom_components.witty_solar_wallbox.select import LED_MODE_SELECT_DESCRIPTION

    assert set(LED_MODE_SELECT_DESCRIPTION.options) == set(LED_MODE_MAP.values())


def test_cp_state_sensor_options_match_registers() -> None:
    """Die ENUM-Optionen des CP-State-Sensors müssen zur Registerkarte passen."""
    from custom_components.witty_solar_wallbox.registers import CP_STATE_OPTIONS, CP_STATES
    from custom_components.witty_solar_wallbox.sensor import SENSOR_DESCRIPTIONS

    cp_state_desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == "cp_state")
    assert set(cp_state_desc.options) == set(CP_STATE_OPTIONS)
    assert set(CP_STATE_OPTIONS) == {state.lower() for state in CP_STATES}
    translated = set(STRINGS["entity"]["sensor"]["cp_state"].get("state", {}))
    assert translated == set(CP_STATE_OPTIONS), "CP-Zustände nicht vollständig übersetzt"


@pytest.mark.parametrize(
    ("sensor_key", "mapping_name"),
    [
        ("led_mode", "LED_MODE_MAP"),
        ("session_state", "SESSION_STATE_MAP"),
        ("error_code", "ERROR_CODE_MAP"),
        ("access_control", "ACCESS_CONTROL_MAP"),
        ("hardware_config", "HARDWARE_CONFIG_MAP"),
        ("pulse_weight", "PULSE_WEIGHT_MAP"),
    ],
)
def test_enum_sensor_options_and_state_translations_match_registers(sensor_key: str, mapping_name: str) -> None:
    """Jeder ENUM-Sensor: Optionen im Code == Mapping-Werte == übersetzte Zustände."""
    from custom_components.witty_solar_wallbox import registers as regs
    from custom_components.witty_solar_wallbox.sensor import SENSOR_DESCRIPTIONS

    mapping = getattr(regs, mapping_name)
    description = next(d for d in SENSOR_DESCRIPTIONS if d.key == sensor_key)

    assert set(description.options) == set(mapping.values())

    translated_states = set(STRINGS["entity"]["sensor"][sensor_key].get("state", {}))
    assert translated_states == set(mapping.values()), (
        f"Zustandstexte für '{sensor_key}' stimmen nicht mit der Registerkarte überein: "
        f"fehlt={set(mapping.values()) - translated_states}, überzählig={translated_states - set(mapping.values())}"
    )


PLACEHOLDER_RE = re.compile(r"\{[a-z_]+\}")


@pytest.mark.parametrize("path", LANGUAGE_FILES, ids=lambda p: p.stem)
def test_placeholders_match_english(path: Path) -> None:
    """{minimum} & Co. müssen in jeder Sprache identisch vorkommen."""
    for key, text in _flatten(_load(path)).items():
        assert sorted(PLACEHOLDER_RE.findall(text)) == sorted(PLACEHOLDER_RE.findall(STRINGS_FLAT[key])), key


def test_exception_translation_exists() -> None:
    """Die Fehlermeldung des Ladestrom-Minimums ist übersetzt und enthält den Platzhalter."""
    assert "{minimum}" in STRINGS["exceptions"]["current_below_minimum"]["message"]


@pytest.mark.parametrize("fname", sorted(PLATFORM_FILES.values()))
def test_entity_category_uses_enum_not_string(fname: str) -> None:
    """entity_category muss ein EntityCategory-Enum sein; ein String lässt Home Assistant die Entity ablehnen."""
    src = (COMPONENT / fname).read_text(encoding="utf-8")
    assert not re.search(r"entity_category\s*=\s*[\"']", src), f"{fname}: entity_category als String"


def test_hardware_limit_amps_supports_enum_and_direct_amps() -> None:
    """Spec-Enum 1..6 und ältere Firmware (Ampere direkt, z. B. 32) werden erkannt."""
    from custom_components.witty_solar_wallbox.registers import hardware_limit_amps

    assert hardware_limit_amps(3) == 16
    assert hardware_limit_amps(6) == 32
    assert hardware_limit_amps(32) == 32
    assert hardware_limit_amps(20) == 20
    assert hardware_limit_amps(None) is None
    assert hardware_limit_amps(0) is None
