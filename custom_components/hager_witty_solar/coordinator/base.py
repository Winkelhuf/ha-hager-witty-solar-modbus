"""DataUpdateCoordinator for Hager Witty Solar."""
from __future__ import annotations

import logging
from datetime import timedelta
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

class WittySolarDataUpdateCoordinator(DataUpdateCoordinator[dict[str, any]]):
    """Class to manage fetching Hager Witty Solar data from Modbus TCP."""

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        """Initialize."""
        self.client = AsyncModbusTcpClient(host=host, port=port)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, any]:
        """Fetch data from Witty Solar wallbox via Modbus."""
        try:
            if not self.client.connected:
                await self.client.connect()

            if not self.client.connected:
                raise UpdateFailed("Failed to connect to Hager Witty Solar via Modbus TCP")

            data = {}

            # 1. Live & Measurement Registers (0x0043 to 0x004F)
            res_live = await self.client.read_holding_registers(address=0x0043, count=13)
            if not res_live.isError():
                regs = res_live.registers
                data["max_current_hw"] = regs[0]
                data["max_current_pp"] = regs[1]
                
                # CP State (Register 0x0045)
                cp_val = regs[2]
                high_byte = cp_val >> 8
                low_byte = cp_val & 0xFF
                data["cp_state"] = f"{chr(high_byte)}{chr(low_byte) if low_byte else ''}".strip()

                data["pwm_value"] = regs[3]
                data["current_phase_1"] = regs[4] / 10.0 if regs[4] != 0x7FFF else 0
                data["current_phase_2"] = regs[5] / 10.0 if regs[5] != 0x7FFF else 0
                data["current_phase_3"] = regs[6] / 10.0 if regs[6] != 0x7FFF else 0
                data["voltage_phase_1"] = regs[7] / 10.0 if regs[7] != 0xFFFF else 0
                data["voltage_phase_2"] = regs[8] / 10.0 if regs[8] != 0xFFFF else 0
                data["voltage_phase_3"] = regs[9] / 10.0 if regs[9] != 0xFFFF else 0
                data["power_phase_1"] = regs[10] if regs[10] != 0xFFFF else 0
                data["power_phase_2"] = regs[11] if regs[11] != 0xFFFF else 0
                data["power_phase_3"] = regs[12] if regs[12] != 0xFFFF else 0

            # 2. Charging Current & Error Code (0x0050 to 0x0054)
            res_cfg = await self.client.read_holding_registers(address=0x0050, count=5)
            if not res_cfg.isError():
                cfg_regs = res_cfg.registers
                data["max_charging_current"] = cfg_regs[0]
                data["max_charging_current_fb"] = cfg_regs[1]
                data["boost_solar_mode"] = cfg_regs[2]
                data["access_control"] = cfg_regs[3]
                data["error_code"] = cfg_regs[4]

            # 3. Energy Session (0x0069 - 0x006A)
            res_energy = await self.client.read_holding_registers(address=0x0069, count=2)
            if not res_energy.isError():
                data["energy_session"] = (res_energy.registers[0] << 16) + res_energy.registers[1]

            # 4. Coils (Status & Switches)
            res_coils = await self.client.read_coils(address=0x0001, count=12)
            if not res_coils.isError():
                bits = res_coils.bits
                data["coil_station_available"] = bits[0]
                data["coil_switch_3_to_1"] = bits[2]
                data["coil_lock_cable"] = bits[5]
                data["coil_enable_rfid_auth"] = bits[10]

            return data

        except ModbusException as error:
            raise UpdateFailed(f"Modbus communication error: {error}") from error

    async def async_write_register(self, address: int, value: int) -> None:
        """Write holding register to wallbox."""
        if not self.client.connected:
            await self.client.connect()
        await self.client.write_register(address, value)
        await self.async_request_refresh()

    async def async_write_coil(self, address: int, value: bool) -> None:
        """Write coil to wallbox."""
        if not self.client.connected:
            await self.client.connect()
        await self.client.write_coil(address, value)
        await self.async_request_refresh()