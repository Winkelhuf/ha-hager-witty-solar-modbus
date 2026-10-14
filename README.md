# Hager Witty Solar Modbus Integration for Home Assistant

[![GitHub Release](https://img.shields.io/github/v/release/Winkelhuf/ha-hager-witty-solar-modbus?include_prereleases&style=flat-square)](https://github.com/Winkelhuf/ha-hager-witty-solar-modbus)
[![License](https://img.shields.io/github/license/Winkelhuf/ha-hager-witty-solar-modbus?style=flat-square)](LICENSE)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://github.com/hacs/integration)

---

## 🇬🇧 English Documentation

This Home Assistant custom component allows local integration and control of the **Hager Witty Solar** EV charging station via Modbus TCP, based on the official Modbus specification v0.28.

### Features
* **Sensors:** Real-time data for phase voltages, currents, and powers, Control Pilot (CP) state, PWM value, charging session energy (Wh), RFID tag UID, and error codes.
* **Switches (Coils):** Lock/unlock station HMI, force 1-phase mode (`Switch3to1`), enable/disable RFID authentication, and toggle EV41 compliance.
* **Number Controls:** Adjust maximum charging current, offline fallback charging current, and HMI LED intensity.
* **Config Flow:** Easy setup directly through the Home Assistant UI (IP address and port).

### Installation via HACS (Recommended)
1. Open HACS in your Home Assistant instance.
2. Go to **Integrations**, click the three dots in the top right corner, and select **Custom repositories**.
3. Add the repository URL: `https://github.com/Winkelhuf/ha-hager-witty-solar-modbus` with the category **Integration**.
4. Click **Install** on the "Hager Witty Solar EVCS" card.
5. Restart Home Assistant.

### Configuration
1. Go to **Settings** -> **Devices & Services** -> **Add Integration**.
2. Search for **Hager Witty Solar**.
3. Enter your wallbox IP address and Modbus port (default: `502`).

---

