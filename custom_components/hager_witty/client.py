"""Async Modbus TCP client for one Hager WittyPlus wallbox.

The wallbox accepts only ONE simultaneous TCP connection (developer's guide,
"Numbers of simultaneous TCP/IP connections: 1"). The client therefore keeps a
single persistent connection and serialises all requests with a lock.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
import inspect
from typing import Any

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import DEFAULT_PORT, DEFAULT_TIMEOUT, DEFAULT_UNIT_ID, LOGGER
from .registers import INFO_CORE_BLOCK, INFO_OPTIONAL_BLOCKS, Block, decode_block


class WittyError(Exception):
    """Base class for all Witty communication errors."""


class WittyConnectionError(WittyError):
    """The TCP connection failed or the wallbox did not answer."""


class WittyRegisterError(WittyError):
    """The wallbox answered with a Modbus exception (e.g. illegal data address)."""


@dataclass(frozen=True, slots=True)
class WittyIdentity:
    """Static information read once from the wallbox."""

    wallbox_id: str | None = None
    product_reference: str | None = None
    software_version: str | None = None
    modbus_version: int | None = None
    mac_address: str | None = None


class WittyClient:
    """Persistent Modbus TCP connection to a single Witty wallbox."""

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        unit_id: int = DEFAULT_UNIT_ID,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialise the client (no connection is opened yet)."""
        self._host = host
        self._port = port
        self._unit_id = unit_id
        self._timeout = timeout
        self._client: AsyncModbusTcpClient | None = None
        self._lock = asyncio.Lock()

    @property
    def host(self) -> str:
        """Return the configured host."""
        return self._host

    # -- connection handling -------------------------------------------------

    async def _async_drop(self) -> None:
        """Close and forget the current connection (caller holds the lock)."""
        client, self._client = self._client, None
        if client is None:
            return
        try:
            result = client.close()
            if inspect.isawaitable(result):
                await result
        except Exception:  # noqa: BLE001 - closing must never raise
            LOGGER.debug("Error while closing the Modbus connection", exc_info=True)

    async def _async_ensure_connected(self) -> AsyncModbusTcpClient:
        """Open the connection if necessary (caller holds the lock)."""
        if self._client is None:
            # Must be created inside the running event loop.
            self._client = AsyncModbusTcpClient(
                self._host,
                port=self._port,
                timeout=self._timeout,
                retries=1,
            )
        if not self._client.connected:
            try:
                connected = await self._client.connect()
            except (ModbusException, OSError, TimeoutError) as err:
                await self._async_drop()
                raise WittyConnectionError(f"Cannot connect to {self._host}:{self._port}: {err}") from err
            if not connected:
                await self._async_drop()
                raise WittyConnectionError(f"Cannot connect to {self._host}:{self._port}")
        return self._client

    async def async_close(self) -> None:
        """Close the connection."""
        async with self._lock:
            await self._async_drop()

    # -- register access -------------------------------------------------------

    async def _async_call(self, method: str, *args: Any) -> Any:
        """Run one Modbus request and translate errors."""
        async with self._lock:
            client = await self._async_ensure_connected()
            try:
                response = await getattr(client, method)(*args, device_id=self._unit_id)
            except (ModbusException, OSError, TimeoutError) as err:
                await self._async_drop()
                raise WittyConnectionError(f"{method} failed: {err or type(err).__name__}") from err

            if response.isError():
                code = getattr(response, "exception_code", None)
                if code is not None:
                    # The wallbox answered, the connection itself is fine.
                    raise WittyRegisterError(f"{method} rejected with Modbus exception code {code}")
                await self._async_drop()
                raise WittyConnectionError(f"{method} failed: {response}")
            return response

    async def async_read(self, address: int, count: int) -> list[int]:
        """Read ``count`` holding registers starting at ``address`` (function 0x03)."""
        response = await self._async_call("read_holding_registers", address, count)
        registers = list(response.registers)
        if len(registers) < count:
            raise WittyConnectionError(f"Short answer for 0x{address:04X}: {len(registers)} of {count} registers")
        return registers

    async def async_write(self, address: int, words: Sequence[int]) -> None:
        """Write one (0x06) or several (0x10) holding registers."""
        if len(words) == 1:
            await self._async_call("write_register", address, words[0])
        else:
            await self._async_call("write_registers", address, list(words))

    async def async_read_block(self, block: Block) -> dict[str, Any]:
        """Read and decode one register block."""
        return decode_block(block, await self.async_read(block.start, block.count))

    async def async_read_identity(self) -> WittyIdentity:
        """Read the static device information.

        Only connection problems raise. If the wallbox rejects an information
        register, the corresponding field is simply left empty.
        """
        values: dict[str, Any] = {}
        for block in (INFO_CORE_BLOCK, *INFO_OPTIONAL_BLOCKS):
            try:
                values.update(await self.async_read_block(block))
            except WittyRegisterError as err:
                LOGGER.debug("Information block %s not available: %s", block.name, err)
        return WittyIdentity(
            wallbox_id=values.get("wallbox_id"),
            product_reference=values.get("product_reference"),
            software_version=values.get("software_version"),
            modbus_version=values.get("modbus_version"),
            mac_address=values.get("mac_address"),
        )
