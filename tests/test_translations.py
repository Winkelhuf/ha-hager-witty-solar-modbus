"""
Konsistenz-Tests für die Übersetzungen.

Sie laufen ohne laufendes Home Assistant und schlagen fehl, wenn
- eine Sprache Schlüssel oder Platzhalter gegenüber Englisch verliert,
- Code und JSON auseinanderlaufen (neue Entität ohne Namen, neuer ENUM-Zustand ohne Text),
- ein Übersetzungs-Key gegen die Home-Assistant-Regeln verstößt.

Eine neue Sprache besteht die Tests, sobald ``translations/<sprache>.json`` alle
Schlüssel von ``en.json`` enthält.
"""

from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

from custom_components.hager_witty.binary_sensor import BINARY_SENSOR_DESCRIPTIONS
from custom_components.hager_witty.button import BUTTON_DESCRIPTIONS
from custom_components.hager_witty.number import NUMBER_DESCRIPTIONS
from custom_components.hager_witty.select import SELECT_DESCRIPTIONS
from custom_components.hager_witty.sensor.descriptions import SENSOR_DESCRIPTIONS
from custom_components.hager_witty.sensor.energy import ENERGY_ENTITY_DESCRIPTIONS
from custom_components.hager_witty.switch import SWITCH_DESCRIPTIONS

COMPONENT = Path(__file__).parent.parent / "custom_components" / "hager_witty"
TRANSLATIONS = COMPONENT / "translations"

# Regel von hassfest für translation_keys (Unterstriche sind erlaubt)
KEY_RE = re.compile(r"^(?!.+[_-]{2})(?![_-])[a-z0-9-_]+(?<![_-])$")
PLACEHOLDER_RE = re.compile(r"\{[a-z_]+\}")


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


EN = _load(TRANSLATIONS / "en.json")
EN_FLAT = _flatten(EN)
LANGUAGE_FILES = sorted(p for p in TRANSLATIONS.glob("*.json") if p.stem != "en")

PLATFORM_DESCRIPTIONS = {
    "sensor": (*SENSOR_DESCRIPTIONS, *ENERGY_ENTITY_DESCRIPTIONS),
    "binary_sensor": BINARY_SENSOR_DESCRIPTIONS,
    "number": NUMBER_DESCRIPTIONS,
    "select": SELECT_DESCRIPTIONS,
    "switch": SWITCH_DESCRIPTIONS,
    "button": BUTTON_DESCRIPTIONS,
}


def test_strings_json_is_the_english_source() -> None:
    """strings.json und translations/en.json sind identisch."""
    assert _load(COMPONENT / "strings.json") == EN


def test_there_are_translations_besides_english() -> None:
    """Mindestens Deutsch muss vorhanden sein."""
    assert LANGUAGE_FILES


@pytest.mark.parametrize("path", LANGUAGE_FILES, ids=lambda p: p.stem)
def test_language_has_exactly_the_english_keys(path: Path) -> None:
    """Keine fehlenden und keine überzähligen Schlüssel gegenüber Englisch."""
    flat = _flatten(_load(path))

    assert not set(EN_FLAT) - set(flat), f"fehlt in {path.name}: {sorted(set(EN_FLAT) - set(flat))}"
    assert not set(flat) - set(EN_FLAT), f"überzählig in {path.name}: {sorted(set(flat) - set(EN_FLAT))}"


@pytest.mark.parametrize("path", LANGUAGE_FILES, ids=lambda p: p.stem)
def test_placeholders_match_english(path: Path) -> None:
    """{register} & Co. müssen in jeder Sprache identisch vorkommen."""
    for key, text in _flatten(_load(path)).items():
        assert sorted(PLACEHOLDER_RE.findall(text)) == sorted(PLACEHOLDER_RE.findall(EN_FLAT[key])), key


@pytest.mark.parametrize("path", [TRANSLATIONS / "en.json", *LANGUAGE_FILES], ids=lambda p: p.stem)
def test_no_empty_texts(path: Path) -> None:
    """Leere Texte würden in Home Assistant nur den Gerätenamen anzeigen."""
    for key, text in _flatten(_load(path)).items():
        assert text.strip(), f"{path.name}: {key} ist leer"


@pytest.mark.parametrize("platform", PLATFORM_DESCRIPTIONS)
def test_every_entity_in_code_has_a_name(platform: str) -> None:
    """Jede Entität aus dem Code hat einen Namen in den Übersetzungen - und umgekehrt."""
    translated = EN["entity"][platform]
    code_keys = {d.key for d in PLATFORM_DESCRIPTIONS[platform]}

    for key in code_keys:
        assert KEY_RE.match(key), f"ungültiger translation_key: {key}"
        assert translated.get(key, {}).get("name"), f"Name fehlt für {platform} '{key}'"
    assert not set(translated) - code_keys, f"Übersetzung ohne Entität ({platform}): {set(translated) - code_keys}"


def test_every_enum_state_has_a_text() -> None:
    """Jeder ENUM-Zustand im Code hat einen Text - und umgekehrt."""
    for description in PLATFORM_DESCRIPTIONS["sensor"]:
        if description.options:
            states = EN["entity"]["sensor"][description.key]["state"]
            assert set(states) == set(description.options), description.key
    for description in SELECT_DESCRIPTIONS:
        states = EN["entity"]["select"][description.key]["state"]
        assert set(states) == set(description.options), description.key


def test_exception_translations_exist() -> None:
    """Fehlermeldungen beim Schreiben sind übersetzt."""
    assert "{error}" in EN["exceptions"]["invalid_value"]["message"]
    assert "{register}" in EN["exceptions"]["write_rejected"]["message"]
    assert "{error}" in EN["exceptions"]["write_failed"]["message"]
