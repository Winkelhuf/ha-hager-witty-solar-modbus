# Changelog

## 0.2.0

- Connection handling for the real EVCS board: small read blocks, handshake on the magic-byte register, reconnect with back-off, optional register ranges and coils are skipped when the wallbox rejects them (older firmware).
- Energy dashboard: *Charged energy (total)* sensor and *Charging power* (measured or estimated from phase currents).
- EMS entities: *Vehicle connected*, *Charging*, *Charging enabled* switch (0 A = stop).
- CP state shown in plain text (German/English).
- Writes are read back and failures are shown in the UI.
- Hardware current limit also accepted as direct ampere value (older firmware).
- Diagnostics download, brand images, CI on Python 3.14, new unit tests.
- README: required wallbox firmware (`7.0.6.0/1.0.3.0` per specification), firmware update note (Hager XEM470 + internet), troubleshooting.
- Fix: `entity_category` is now a proper `EntityCategory` enum (diagnostic/config entities were rejected by Home Assistant).

## 0.1.0

- Initial version based on EVCS_Modbus v0.28 (holding registers and coils).
