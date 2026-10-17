"""Diagnose-Daten für die Hager Witty Solar Wallbox (ohne personenbezogene Werte)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

TO_REDACT = {CONF_HOST, "serial_number", "rfid_tag_uid"}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Gibt Konfiguration, Geräteinfo, Firmware und nicht unterstützte Register zurück."""
    coordinator = entry.runtime_data.coordinator
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "device_info": async_redact_data(dict(coordinator.device_info_data), TO_REDACT),
        "unsupported_register_ranges": [f"0x{start:04X}" for start in sorted(coordinator._unsupported_segments)],
        "unsupported_coils": [f"0x{addr:04X}" for addr in sorted(coordinator._unsupported_coils)],
        "read_block_size": coordinator._chunk_size,
        "data": async_redact_data(dict(coordinator.data or {}), TO_REDACT),
    }
