"""Config flow für die Hager Witty Modbus Integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .client import WittyClient, WittyError, WittyIdentity
from .const import (
    CONF_UNIT_ID,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UNIT_ID,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
    }
)
RECONFIGURE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
    }
)


async def _async_identify(host: str, port: int, unit_id: int) -> WittyIdentity:
    """Verbinde zur Wallbox und lies die Kennung (wirft WittyError bei Verbindungsproblemen)."""
    client = WittyClient(host, port, unit_id)
    try:
        return await client.async_read_identity()
    finally:
        await client.async_close()


class WittyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handhabung des Config Flows für Hager Witty."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> WittyOptionsFlow:
        """Optionen (Abfrageintervall) anbieten."""
        return WittyOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Erster Schritt bei der manuellen Einrichtung (IP-Adresse der Wallbox)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            # Jede Witty hat ihre eigene IP: dieselbe IP nicht zweimal einrichten.
            self._async_abort_entries_match({CONF_HOST: host})

            try:
                identity = await _async_identify(host, user_input[CONF_PORT], user_input[CONF_UNIT_ID])
            except WittyError as err:
                LOGGER.debug("Connection test to %s failed: %s", host, err)
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                LOGGER.exception("Unexpected error while connecting to %s", host)
                errors["base"] = "unknown"
            else:
                # Die Kennung der Wallbox bleibt auch bei einer neuen IP gleich.
                await self.async_set_unique_id(identity.wallbox_id or host)
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                return self.async_create_entry(
                    title=user_input[CONF_NAME].strip() or DEFAULT_NAME,
                    data={
                        CONF_HOST: host,
                        CONF_PORT: user_input[CONF_PORT],
                        CONF_UNIT_ID: user_input[CONF_UNIT_ID],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Neue IP-Adresse / neuen Port der Wallbox eintragen."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()

            # Die Witty erlaubt nur eine Verbindung: die laufende Verbindung der
            # Integration kurz freigeben, damit der Test durchkommt (sie verbindet
            # sich beim nächsten Abruf automatisch wieder).
            runtime_data = getattr(entry, "runtime_data", None)
            if runtime_data is not None:
                await runtime_data.client.async_close()

            try:
                identity = await _async_identify(host, user_input[CONF_PORT], user_input[CONF_UNIT_ID])
            except WittyError as err:
                LOGGER.debug("Connection test to %s failed: %s", host, err)
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                LOGGER.exception("Unexpected error while connecting to %s", host)
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(identity.wallbox_id or entry.unique_id)
                self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_HOST: host,
                        CONF_PORT: user_input[CONF_PORT],
                        CONF_UNIT_ID: user_input[CONF_UNIT_ID],
                    },
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(RECONFIGURE_SCHEMA, user_input or entry.data),
            errors=errors,
        )


class WittyOptionsFlow(OptionsFlow):
    """Optionen: Abfrageintervall."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Abfrageintervall in Sekunden einstellen."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                    vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
