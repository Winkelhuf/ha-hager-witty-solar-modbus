# Hager Witty Modbus Integration for Home Assistant

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.12%2B-blue.svg)](https://www.home-assistant.io/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

🌐 Deutsche Version: [README.de.md](README.de.md)

Local Home Assistant integration for **Hager Witty (WittyPlus) wallboxes** that are **not** part of a Hager flow system,
e.g. wallboxes controlled by a third-party energy manager. Every wallbox is addressed **directly by its IP address** over
**Modbus TCP** – no cloud, no auto-discovery. It implements the complete register map of the
*WittyPlus ModbusTCP server developer's Guide v1.0.1*.

> Looking for the Hager flow (XEM470) integration with auto-discovery? See
> [ha-hager-flow](https://github.com/Winkelhuf/ha-hager-flow).

---

## ⚠️ Read this first

* **Only one Modbus TCP connection.** The Witty accepts a **single** TCP connection at a time. If your energy manager
  talks to the wallbox via Modbus TCP, Home Assistant **cannot** connect at the same time (and vice versa). In that case
  use the energy manager's own Home Assistant integration for the shared data, or disconnect the other client.
* **Enable Modbus TCP first.** It is switched off by default and is enabled with the **Hager mobile app**.
* **Fallback values.** If the Modbus client disappears (link down, TCP reset, read/write timeout), the wallbox applies its
  *fallback* values (current limit, availability, phase mode) – immediately or after 30 s (see *Delay fallback*). Set the
  fallback entities to values you are happy with. Home Assistant only writes when **you** change an entity or press a button.
* **Not tested on real hardware yet.** The register map was implemented from the manufacturer's guide. Please report
  anything that looks wrong (with the debug log) – see [Known open points](#-known-open-points).

---

## 📋 Prerequisites

* Hager WittyPlus wallbox with Modbus TCP enabled, reachable in your network (**static IP / DHCP reservation recommended**).
* Port **502**, Modbus unit identifier **1** (default of the wallbox).
* Home Assistant **2025.12** or newer.

---

## 📊 Entities

Each wallbox becomes **one device**. Entity names follow your Home Assistant language (English / Deutsch); status texts
are translated.

### Sensors
| Entity | Register | Notes |
|---|---|---|
| **Status** | `0x302B` | Plain-text state of the wallbox (idle, waiting for …, charging (solar), error …) |
| **Control pilot state** | `0x3008` | A1 … F according to DIN EN 61851 |
| **Power**, **Power L1/L2/L3** | `0x3013`, `0x3010-12` | W |
| **Current L1/L2/L3** | `0x300A-0C` | A (`0x7FFF` = invalid → unavailable) |
| **Voltage L1/L2/L3** | `0x300D-0F` | V |
| **Energy current session** | `0x5000` | Wh → kWh, `total_increasing` (resets with each session) |
| **Energy total** | *calculated* | Ever-increasing kWh counter for the **Energy dashboard** (sums the session energy, survives restarts) |
| **Charging duration** | `0x500A` | Time in state C |
| **Session start / end** | `0x5002`, `0x5006` | Timestamps |
| **Session badge**, **Session badge type**, **Last stop reason** | `0x500C-0x5013` | Stop reason in plain text |
| **Session state** | `0x5014` | No session / running / ended |
| **Cable lock** | `0x3025` | Unlocked, locked, tethered, blocked … |
| Diagnostic: **PWM duty cycle**, **Hardware current limit**, **Cable current limit**, **Wallbox clock**\*, **Last RFID tag**\* | | \*disabled by default |

### Binary sensors
**Charging**, **Vehicle connected**, **Error** (derived from status / control pilot), **Clock set** (diagnostic).

### Controls
| Entity | Register | Notes |
|---|---|---|
| **Maximum charging current** (Number, 0–32 A) | `0x301E` | The value an energy manager would set. PWM resolution of the wallbox is 0.6 A. |
| **Maximum charging current (fallback)** (Number) | `0x301F` | Applied when the Modbus client is lost |
| **Phase mode** (Select: *3 phases* / *1 phase only*) | `0x3022` | **1-phase ↔ 3-phase switching** |
| **Phase mode (fallback)** (Select) | `0x3023` | |
| **Available** (Switch) | `0x3020` | Off = wallbox locked (HMI red) |
| **Available (fallback)** (Switch) | `0x3021` | |
| **Delay fallback by 30 s** (Switch) | `0x3026` | |
| **Synchronize clock** (Button) | `0x3000` | Writes the current UTC time to the wallbox |
| **RFID feedback**\* (Select) | `0x400B` | Answer to a presented RFID tag – disabled by default |

The **RFID registers** are optional: they are only served while RFID authentication is active. If the wallbox rejects
them they are skipped and retried every 5 minutes, without log noise. Any other rejected block is logged once as a warning.

### Energy dashboard
The wallbox only reports the energy of the **current** session (it restarts at 0 with every new session). **Energy total**
adds up the increments of that register and keeps counting correctly across sessions, so it can be used as an
*individual device* in **Settings → Dashboards → Energy**. Its running total is restored after restarts.

Limitation: if a new session starts while Home Assistant is offline and has already charged *more* than the previous
session's last known value, only the difference is counted. This only affects long polling gaps.

---

## 🚀 Installation

### HACS – custom repository
1. **HACS → ⋮ → Custom repositories**
2. Repository: `https://github.com/Winkelhuf/ha-hager-witty`, type **Integration** → **Add**
3. Download **Hager Witty Modbus** and **restart** Home Assistant.

### Manual
Copy `custom_components/hager_witty/` to `<config>/custom_components/` and restart.

### Updates
Publish a **GitHub release with a version tag** (e.g. `v0.1.1`) and raise `version` in
`custom_components/hager_witty/manifest.json` (and `VERSION` in `const.py`) – HACS detects updates from releases.

---

## ⚙️ Configuration

1. **Settings → Devices & services → Add integration → "Hager Witty Modbus"**
2. Enter **IP address**, a **name** (e.g. *Witty Garage*), port (502) and unit ID (1).
3. Repeat for every wallbox (each has its own IP; the same IP cannot be added twice).

* **Options** (gear icon): polling interval, default 5 s (2–60 s).
* **Reconfigure** (⋮ menu of the entry): change IP/port after a router change – the wallbox is recognized by its unique id.

---

## 🧭 Known open points

The guide is ambiguous in a few places. This is how the integration interprets them – please report if your wallbox
behaves differently:

1. **Addresses are hexadecimal** (`301E` = 12318) and used as protocol addresses without offset.
2. **Multi-register values** (uint32/int32/uint64/timestamps) use the standard Modbus word order, most significant word first.
3. **Invalid current** is `0x7FFF` (the guide prints `0x7FFFF` for a 16-bit register).
4. **Session energy (`0x5000`)** is read as uint32 in **Wh**; **charging duration (`0x500A`)** as uint32 in seconds.
5. **Control pilot state (`0x3008`)** is read as a 2-character ASCII string in one register.
6. **Session badge** (`0x500C/0x500D`) and RFID tag (`0x4001/0x4002`) are shown as hex UID.

---

## 🛠️ Tech stack

Async `pymodbus` (3.11+), a single persistent connection guarded by a lock (the wallbox allows only one), the
`DataUpdateCoordinator` pattern with **8 contiguous block reads per update** (no undocumented addresses), translated
entity names/states, config + options + reconfigure flow, GitHub Actions for **hassfest**, **HACS** and **pytest**.
The register map lives in `registers.py` without Home Assistant imports and is covered by unit tests.

---

## Built with AI

This repository was developed with significant assistance from an AI coding assistant (Claude), based on the structure of
the [ha-hager-flow](https://github.com/Winkelhuf/ha-hager-flow) integration. Register interpretation was checked by unit
tests, but the integration has **not yet been tested against a real wallbox**.

## Disclaimer

Not affiliated with or endorsed by Hager. "hager" and "Witty" are trademarks of their respective owners. Writing to a
charging station can affect charging behavior – use at your own risk.

## 📜 License

MIT – see [LICENSE](LICENSE).
