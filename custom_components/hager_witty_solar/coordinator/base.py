"""DataUpdateCoordinator for the Hager Witty Modbus integration."""

from __future__ import annotations

from datetime import timedelta
import time
from typing import TYPE_CHECKING, Any

from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo, format_mac
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..client import WittyClient, WittyConnectionError, WittyIdentity, WittyRegisterError
from ..const import DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER, OPTIONAL_BLOCK_RETRY_SECONDS
from ..registers import POLL_BLOCKS, REGISTER_BY_KEY, decode_register, derive_values, encode_value

if TYPE_CHECKING:
    from ..data import WittyConfigEntry


class WittyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls all documented Witty registers in a few contiguous block reads."""

    config_entry: WittyConfigEntry

    def __init__(self, hass: HomeAssistant, entry: WittyConfigEntry, client: WittyClient) -> None:
        """Initialise the coordinator."""
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.data[CONF_HOST]}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.identity = WittyIdentity()
        # block name -> monotonic time until which an optional block is not requested
        self._skip_until: dict[str, float] = {}
        # blocks for which the "rejected" warning was already logged (log it only once)
        self._warned_blocks: set[str] = set()

    # -- device ------------------------------------------------------------------

    @property
    def wallbox_id(self) -> str:
        """Stable id of this wallbox (used for all unique ids)."""
        return self.config_entry.unique_id or self.config_entry.data[CONF_HOST]

    @property
    def device_info(self) -> DeviceInfo:
        """Device registry information shared by all entities of this wallbox."""
        identity = self.identity
        connections = {(CONNECTION_NETWORK_MAC, format_mac(identity.mac_address))} if identity.mac_address else set()
        return DeviceInfo(
            identifiers={(DOMAIN, self.wallbox_id)},
            connections=connections,
            manufacturer="Hager",
            model=identity.product_reference or "WittyPlus",
            name=self.config_entry.title,
            serial_number=identity.wallbox_id,
            sw_version=identity.software_version,
        )

    # -- updates -----------------------------------------------------------------

    async def _async_setup(self) -> None:
        """Read the static device information once (before the first refresh)."""
        try:
            self.identity = await self.client.async_read_identity()
        except WittyConnectionError as err:
            raise UpdateFailed(f"Cannot reach the Witty at {self.client.host}: {err}") from err

    async def _async_update_data(self) -> dict[str, Any]:
        """Read all blocks and return the decoded values."""
        data: dict[str, Any] = {}
        answered = 0
        now = time.monotonic()

        for block in POLL_BLOCKS:
            if block.optional and now < self._skip_until.get(block.name, 0.0):
                continue
            try:
                data.update(await self.client.async_read_block(block))
            except WittyRegisterError as err:
                # The wallbox is reachable but does not serve this block.
                if block.optional:
                    LOGGER.debug("Optional block %s not available, retrying later: %s", block.name, err)
                    self._skip_until[block.name] = now + OPTIONAL_BLOCK_RETRY_SECONDS
                elif block.name not in self._warned_blocks:
                    self._warned_blocks.add(block.name)
                    LOGGER.warning("Register block %s (0x%04X) was rejected: %s", block.name, block.start, err)
                answered += 1
                continue
            except WittyConnectionError as err:
                raise UpdateFailed(f"Communication with the Witty at {self.client.host} failed: {err}") from err
            answered += 1
            self._skip_until.pop(block.name, None)

        if not answered:  # pragma: no cover - defensive, POLL_BLOCKS is never empty
            raise UpdateFailed("No register block could be read")

        data.update(derive_values(data))
        return data

    # -- writing -----------------------------------------------------------------

    async def async_write_value(self, key: str, value: float) -> None:
        """Write a physical value to the R/W register ``key`` and update the state."""
        register = REGISTER_BY_KEY[key]
        try:
            words = encode_value(register, value)
        except ValueError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="invalid_value",
                translation_placeholders={"error": str(err)},
            ) from err

        try:
            await self.client.async_write(register.address, words)
        except WittyRegisterError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_rejected",
                translation_placeholders={"register": f"0x{register.address:04X}", "error": str(err)},
            ) from err
        except WittyConnectionError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={"error": str(err)},
            ) from err

        # Show the new value immediately, the next poll confirms it.
        updated = {**(self.data or {}), key: decode_register(register, words)}
        self.async_set_updated_data(updated)
        await self.async_request_refresh()
