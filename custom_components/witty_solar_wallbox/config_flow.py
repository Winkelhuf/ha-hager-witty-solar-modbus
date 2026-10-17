"""Config Flow für die Witty-Solar-Wallbox-Integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from pymodbus.client import ModbusTcpClient

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SLAVE

from .const import DEFAULT_PORT, DOMAIN, LOGGER, UNIT_ID
from .registers import MAGICBYTE_VALUE, REG_MAGICBYTE


class WittySolarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config Flow für die Hager Witty Solar Wallbox (EVCS/B1280-Board)."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> Any:
        """Erster (und einziger) Schritt: Host und Port abfragen."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            unit_id = user_input[CONF_SLAVE]

            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()

            can_connect = await self.hass.async_add_executor_job(self._test_connection, host, port, unit_id)
            if can_connect:
                return self.async_create_entry(title="Witty Solar Wallbox", data=user_input)
            errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_SLAVE, default=UNIT_ID): vol.All(int, vol.Range(min=0, max=255)),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def _test_connection(host: str, port: int, unit_id: int) -> bool:
        """Prüft die Erreichbarkeit über das Magicbyte-Register (0x0000, erwarteter Wert 0xE3DC)."""
        client = ModbusTcpClient(host=host, port=port)
        try:
            if not client.connect():
                return False
            result = client.read_holding_registers(REG_MAGICBYTE, count=1, device_id=unit_id)
            return result is not None and not result.isError() and result.registers[0] == MAGICBYTE_VALUE
        except Exception as err:  # noqa: BLE001
            LOGGER.debug("Verbindungstest zur Witty-Solar-Wallbox fehlgeschlagen: %s", err)
            return False
        finally:
            client.close()
