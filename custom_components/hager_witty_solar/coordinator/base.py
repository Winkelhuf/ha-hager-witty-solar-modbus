"""DataUpdateCoordinator for Hager Witty Solar."""
from __future__ import annotations

import logging
from datetime import timedelta
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    REG_CP_STATE,
    REG_PWM_VALUE,
    REG_CURRENT_PHASE_1,
    REG_CURRENT_PHASE_2,
    REG_CURRENT_PHASE_3,
    REG_VOLTAGE_PHASE_1,
    REG_VOLTAGE_PHASE_2,
    REG_VOLTAGE_PHASE_3,
    REG_POWER_PHASE_1,
    REG_POWER_PHASE_2,
    REG_POWER_PHASE_3,
    REG_MAX_CHARGING_CURRENT,
    REG_MAX_CHARGING_CURRENT_FB,
    REG_ERROR_CODE,
    REG_ENERGY_SESSION,
    REG_LED_INTENSITY,
    COIL_STATION_AVAILABLE,
    COIL_SWITCH_3_TO_1,
    COIL_LOCK_CABLE,
    COIL_ENABLE_RFID_AUTH,
    COIL_EV41_COMPLIANCE,
    COIL_DHCP_SETTING,
)

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

            # Holding Registers auslesen (Beispiel-Blöcke oder Einzelregister)
            # Live-Werte (CP State, PWM, Strom, Spannung, Leistung)
            res_live = await self.client.read_holding_registers(address=0x0045, count=11)
            if not res_live.isError():
                data["cp_state"] = chr(res_live.registers[0] >> 8) + chr(res_live.registers[0] & 0xFF)
                data["pwm_value"] = res_live.registers[1]
                data["current_phase_1"] = res_live.registers[2] / 10.0
                data["current_phase_2"] = res_live.registers[3] / 10.0 if res_live.registers[3] != 0x7FFF else 0
                data["current_phase_3"] = res_live.registers[4] / 10.0 if res_live.registers[4] != 0x7FFF else 0
                data["voltage_phase_1"] = res_live.registers[5] / 10.0 if res_live.registers[5] != 0xFFFF else 0
                data["voltage_phase_2"] = res_live.registers[6] / 10.0 if res_live.registers[6] != 0xFFFF else 0
                data["voltage_phase_3"] = res_live.registers[7] / 10.0 if res_live.registers[7] != 0xFFFF else 0
                data["power_phase_1"] = res_live.registers[8] if res_live.registers[8] != 0xFFFF else 0
                data["power_phase_2"] = res_live.registers[9] if res_live.registers[9] != 0xFFFF else 0
                data["power_phase_3"] = res_live.registers[10] if res_live.registers[10] != 0xFFFF else 0

            # Charging Current & Error
            res_cfg = await self.client.read_holding_registers(address=0x0050, count=6)
            if not res_cfg.isError():
                data["max_charging_current"] = res_cfg.registers[0]
                data["max_charging_current_fb"] = res_cfg.registers[1]
                data["boost_solar_mode"] = res_cfg.registers[2]
                data["access_control"] = res_cfg.registers[3]
                data["error_code"] = res_cfg.registers[5]

            # Energy Session (Registers 0x0069 - 0x006A)
            res_energy = await self.client.read_holding_registers(address=0x0069, count=2)
            if not res_energy.isError():
                # 32-bit integer combination
                energy_wh = (res_energy.registers[0] << 16) + res_energy.registers[1]
                data["energy_session"] = energy_wh

            # Coils auslesen (Schalter & Status)
            res_coils = await self.client.read_coils(address=0x0001, count=11)
            if not res_coils.isError():
                data["coil_station_available"] = res_coils.bits[0]
                data["coil_switch_3_to_1"] = res_coils.bits[2]
                data["coil_lock_cable"] = res_coils.bits[5]
                data["coil_enable_rfid_auth"] = res_coils.bits[10]

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