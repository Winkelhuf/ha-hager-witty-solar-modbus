<p align="center">
  <img src="custom_components/witty_solar_wallbox/brand/logo.png" alt="Hager Witty Solar Wallbox" height="96">
</p>

# Hager Witty Solar Wallbox Integration for Home Assistant

[![Validate](https://github.com/Winkelhuf/ha-hager-witty-solar-modbus/actions/workflows/validate.yml/badge.svg)](https://github.com/Winkelhuf/ha-hager-witty-solar-modbus/actions/workflows/validate.yml)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.12%2B-blue.svg)](https://www.home-assistant.io/)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

🌐 **Languages:** **English** | [Deutsch](README.de.md)

A Home Assistant custom integration to monitor and control a **Hager Witty Solar** wallbox locally over **Modbus TCP**. It implements the generic EVCS communication-board interface from *"EVCS_Modbus v0.28"* (holding registers **and** coils) and talks directly to the wallbox's IP address — no cloud, no EMS gateway.

> Using a **WittyPlus** wallbox? That model has a different register map and its own integration: [`ha-hager-witty-modbus`](https://github.com/Winkelhuf/ha-hager-witty-modbus).

---

## ⚠️ Required wallbox firmware

The register map in this integration follows **EVCS_Modbus v0.28**. According to its revision history, that document refers to **Modbus software v1.0.3.0 (compatible with B1280 v7.0.6.0)**. Several features (session energy, session state, timestamps, date/time sync, RFID authentication coil, LED intensity) were only added to the specification after Modbus software v1.0.2.0.

| | Version string on the device page ("Firmware") |
|---|---|
| **Required for the full feature set** | at least **`7.0.6.0/1.0.3.0`** (controller / communication board) |
| **Tested so far** | `7.0.5.0/1.0.2.0` on a Hager `XEVFR` — **works with reduced functionality** (see below) |

The format is *wallbox controller version / communication board version*, as defined in §3.3.7 of the specification. The minimum version above is derived from the specification's revision history; it has not yet been verified on a wallbox running the newer firmware.

### What works with the older firmware `7.0.5.0/1.0.2.0`

Verified on a real wallbox: connection, reading of CP state, phase currents, hardware/cable current limits, error code and coils `0x0000`–`0x0008`, and **writing** of the *maximum charging current*, *LED mode* and *Only 1 phase charging* (the new value shows up after the next poll). Not yet verified on hardware: *Station available*, *Lock cable*, the *Charging enabled* switch (`0 A`), and the derived entities (*Vehicle connected*, *Charging*, estimated power, charged-energy counter) while a car is charging.

That firmware **rejects** these registers/coils (Modbus "illegal data address"); the matching entities show *unknown* and are skipped automatically after three failed attempts:

| Missing on `7.0.5.0/1.0.2.0` | Affected entities |
|---|---|
| Register `0x0066` | LED intensity |
| Register `0x0069` | Energy current session |
| Register `0x006B` | Session start / session end |
| Register `0x006F` | Session state, meter type |
| Register `0x0071` | Wallbox clock (automatic time sync) |
| Coils `0x0009`–`0x000E` | RFID authentication switch, meter inconsistency, date/time not set, automatic session acknowledgement |

This unit also has **no energy/power meter** (voltage and power registers return the "invalid" marker), so charging power and the energy counter are *estimates* — see *Energy dashboard & EMS* below.

### How to update the wallbox firmware

A Witty wallbox can only be updated if it **has been connected at least once to a Hager `XEM470` with internet access**. Without that, the update is not possible. Please ask your installer or Hager for the update procedure; this integration does not update firmware.

---

## 📋 Features

- ⚡ **100 % local** — Modbus TCP only, no cloud.
- 🔌 **Live charging data:** CP state in plain text, current / voltage / power per phase (values the unit cannot measure are shown as *unknown*), session energy, session start/end, error code, cable current limit (PP), hardware current limit.
- 🎚️ **Maximum charging current** (register `0x0050`): slider, capped by the hardware limit. `1–5 A` is rejected (below the IEC 61851 minimum of 6 A).
- ▶️ **Charging enabled** switch: `off` writes `0 A` (valid per spec, prevents charging), `on` restores the previous current. *This is not a dedicated start/stop command of the wallbox — please verify with a connected car that `0 A` reliably pauses charging on your firmware.*
- 🚀 **Boost switch:** sets the maximum charging current to the hardware limit and restores your previous value when switched off.
- 🔀 **Phase switching:** `Only 1 phase charging` (coil `0x0003`). Only effective on units that can switch 3↔1 phase; applied on the next B2→C2 transition.
- 🚦 **Station available** (coil `0x0001`), 🔒 **Lock cable permanently** (coil `0x0006`), 🪪 **RFID authentication** (coil `0x000A`, newer firmware).
- 💡 **LED mode** (register `0x0052`) and **LED intensity** (`0x0066`, newer firmware).
- ✅ **Write verification:** every command is read back. If the wallbox rejects it, or accepts it without adopting the value, Home Assistant shows an error and the log contains `… written=…, read back=…`.
- 🩺 **Diagnostics:** device information (manufacturer, product, serial, firmware), access control, hardware configuration, RFID reader, socket M2, key-switch position, and a downloadable diagnostics file.

## 🔋 Energy dashboard & EMS

| Need | Entity |
|---|---|
| Energy dashboard consumer | **Charged energy (total)** — kWh, state class `total_increasing`, survives restarts |
| Power | **Charging power** — measured if the wallbox has a meter, otherwise **estimated** from phase currents × voltage (230 V per phase if no voltage is measured); attribute `estimated` tells which |
| Plug sensor | **Vehicle connected** (CP state A = no, B/C = yes) |
| Charging sensor | **Charging** (CP state C2 *and* at least 0.5 A) |
| Current control | **Maximum charging current** (number) |
| Start / stop | **Charging enabled** (switch, `0 A` = stop) |
| Phase switching | **Only 1 phase charging** (switch) |

> **Accuracy:** the *Charged energy (total)* sensor integrates the charging power over time. Without a meter in the wallbox it is an **estimate, not a calibrated value**, and gaps longer than two minutes (e.g. Home Assistant restart) are not extrapolated. On wallboxes with a meter and newer firmware the measured power is used.
>
> **Not available from the wallbox:** vehicle state of charge (use your car's integration) and a "charging mode / force state" selection (the *LED mode* select only changes the LED, **not** the charging power).

## 🚀 Installation

### Option 1: HACS custom repository
1. In Home Assistant open **HACS → Integrations**.
2. Click **⋮ → Custom repositories** and add `https://github.com/Winkelhuf/ha-hager-witty-solar-modbus` as type **Integration**.
3. Download **Hager Witty Solar Wallbox** and restart Home Assistant.

### Option 2: Manual
1. Copy `custom_components/witty_solar_wallbox` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

## ⚙️ Configuration

1. **Settings → Devices & services → Add integration** → search for **"Hager Witty Solar Wallbox"**.
2. Enter **host/IP**, **port** (default `502`) and **Modbus unit ID** (default `1`).
3. Submit. The connection test reads the magic-byte register (`0x0000`, expected `0xE3DC`).

**Prerequisites:** the wallbox's communication board is reachable on your network (use a static or reserved IP) on TCP port **502**, and Home Assistant is **2025.12** or newer.

> [!IMPORTANT]
> **Use only one Modbus client at a time.** The specification does not say whether the communication board supports several simultaneous TCP connections. To be safe, stop other Modbus tools, other integrations for the same wallbox and old test entries before setting this one up.

The integration polls every **10 seconds** and reads small register blocks (in our tests the board reset the connection on a 64-register request).

## 🛠️ Troubleshooting

| Problem | What to do |
|---|---|
| *Connection reset by peer* / *Failed to connect* | Make sure no other Modbus client is connected, power-cycle the wallbox and try again. |
| Entities are listed but *unavailable*, no device shown | Hard-reload the browser (Ctrl+F5 / Cmd+Shift+R). Remove stale entities of earlier test entries under *Settings → Devices & services → Entities*. |
| Many entities show *unknown* | Likely older wallbox firmware, see *Required wallbox firmware* above. |
| An entity change is "not adopted" | The wallbox accepted the write but kept the old value; check the firmware and the log. |

Enable debug logging and attach the log when opening an issue:

```yaml
logger:
  default: warning
  logs:
    custom_components.witty_solar_wallbox: debug
    pymodbus: debug
```

## 🚧 Known limitations

- Not exposed (yet): RFID idTag feedback, generic blink/colour, fallback values for offline operation (`0x0051`, coils `0x0002`/`0x0004`/`0x0009`), EV41 compliance, DHCP/static-IP settings, firmware/configuration update.
- One wallbox per config entry; add the integration once per wallbox/IP.
- Verified on **one** wallbox with firmware `7.0.5.0/1.0.2.0`. The newer-firmware features are implemented from the specification and **not yet tested on real hardware**. Please report anything that behaves differently, including your firmware version.

## 🧪 Development

```bash
pip install pytest pytest-homeassistant-custom-component pymodbus   # requires Python >= 3.14
pytest tests/ -v
```

GitHub Actions runs **hassfest**, **HACS validation** and **pytest** on every push and pull request. See [CONTRIBUTING.md](CONTRIBUTING.md) and the [CHANGELOG](CHANGELOG.md).

## Built with AI

This repository was developed with significant assistance from AI coding assistants (Gemini, Claude). Community integrations may benefit from extensive AI assistance when their actual review, testing, limitations and maturity are communicated honestly. These safeguards improve verifiability but do not guarantee correctness.

**Testing status:** automated tests cover translations, register tables and the coordinator logic; the integration has been exercised on one real wallbox (see above).

## Disclaimer

This integration is not affiliated with or endorsed by Hager. "Hager" and "Witty" are trademarks of their respective owners. Controlling a charging station can affect your electrical installation and vehicle — use at your own risk.

## 📜 License

MIT — see [LICENSE](LICENSE).
