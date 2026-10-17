<p align="center">
  <img src="custom_components/witty_solar_wallbox/brand/logo.png" alt="Hager Witty Solar Wallbox" height="96">
</p>

# Hager Witty Solar Wallbox Integration für Home Assistant

[![Validate](https://github.com/Winkelhuf/ha-hager-witty-solar-modbus/actions/workflows/validate.yml/badge.svg)](https://github.com/Winkelhuf/ha-hager-witty-solar-modbus/actions/workflows/validate.yml)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.12%2B-blue.svg)](https://www.home-assistant.io/)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

🌐 **Sprachen:** [English](README.md) | **Deutsch**

Eine Home-Assistant-Integration zur lokalen Überwachung und Steuerung einer **Hager Witty Solar** Wallbox über **Modbus TCP**. Sie setzt die generische EVCS-Kommunikationsboard-Schnittstelle aus *„EVCS_Modbus v0.28"* um (Holding-Register **und** Coils) und spricht die Wallbox direkt über ihre IP-Adresse an – ohne Cloud, ohne EMS-Gateway.

> Du hast eine **WittyPlus**-Wallbox? Die hat eine andere Registerkarte und eine eigene Integration: [`ha-hager-witty-modbus`](https://github.com/Winkelhuf/ha-hager-witty-modbus).

---

## ⚠️ Benötigter Firmware-Stand der Wallbox

Die Registerkarte dieser Integration folgt **EVCS_Modbus v0.28**. Laut Änderungshistorie bezieht sich dieses Dokument auf **Modbus-Software v1.0.3.0 (kompatibel mit B1280 v7.0.6.0)**. Mehrere Funktionen (Session-Energie, Session-Status, Zeitstempel, Datum/Uhrzeit-Sync, RFID-Coil, LED-Helligkeit) wurden erst nach Modbus-Software v1.0.2.0 in die Spezifikation aufgenommen.

| | Versionsangabe auf der Geräteseite („Firmware“) |
|---|---|
| **Für den vollen Funktionsumfang nötig** | mindestens **`7.0.6.0/1.0.3.0`** (Controller / Kommunikationsboard) |
| **Bisher getestet** | `7.0.5.0/1.0.2.0` an einer Hager `XEVFR` — **läuft mit eingeschränktem Funktionsumfang** (siehe unten) |

Das Format lautet *Version des Wallbox-Controllers / Version des Kommunikationsboards* (§3.3.7 der Spezifikation). Die genannte Mindestversion ist aus der Änderungshistorie der Spezifikation abgeleitet und wurde noch nicht an einer Wallbox mit neuerer Firmware überprüft.

### Was mit der älteren Firmware `7.0.5.0/1.0.2.0` funktioniert

An einer echten Wallbox geprüft: Verbindung, Lesen von CP-Status, Phasenströmen, Hardware-/Kabel-Stromlimit, Fehlercode und Coils `0x0000`–`0x0008` sowie **Schreiben** von *Maximalem Ladestrom*, *LED-Modus* und *Nur 1 Phase laden* (der neue Wert erscheint nach dem nächsten Abruf). Noch nicht an Hardware geprüft: *Ladestation verfügbar*, *Kabel dauerhaft verriegeln*, der Schalter *Laden freigegeben* (`0 A`) und die abgeleiteten Entities (*Fahrzeug angeschlossen*, *Lädt*, geschätzte Leistung, Energiezähler) während ein Auto lädt.

Diese Firmware **lehnt** folgende Register/Coils ab (Modbus „illegal data address“). Die zugehörigen Entities zeigen *unbekannt* und werden nach drei Fehlversuchen automatisch übersprungen:

| Fehlt in `7.0.5.0/1.0.2.0` | Betroffene Entities |
|---|---|
| Register `0x0066` | LED-Helligkeit |
| Register `0x0069` | Energie aktuelle Session |
| Register `0x006B` | Session-Start / Session-Ende |
| Register `0x006F` | Session-Status, Zählertyp |
| Register `0x0071` | Uhr der Wallbox (automatischer Zeit-Sync) |
| Coils `0x0009`–`0x000E` | RFID-Authentifizierung, Zähler-Inkonsistenz, Datum/Uhrzeit nicht gesetzt, automatische Session-Quittierung |

Dieses Gerät hat außerdem **keinen Energie-/Leistungszähler** (Spannungs- und Leistungsregister liefern den „ungültig“-Wert). Ladeleistung und Energiezähler sind deshalb *Schätzungen* – siehe *Energie-Dashboard & EMS* unten.

### So aktualisierst du die Firmware der Wallbox

Eine Witty-Wallbox lässt sich nur aktualisieren, wenn sie **mindestens einmal mit einem Hager `XEM470` mit Internetzugang verbunden war**. Ohne diese Verbindung ist ein Update nicht möglich. Das Vorgehen erfragst du bei deinem Installateur oder bei Hager; diese Integration aktualisiert keine Firmware.

---

## 📋 Funktionen

- ⚡ **100 % lokal** – nur Modbus TCP, keine Cloud.
- 🔌 **Live-Ladedaten:** CP-Status im Klartext, Strom / Spannung / Leistung je Phase (nicht messbare Werte erscheinen als *unbekannt*), Session-Energie, Session-Start/-Ende, Fehlercode, Kabel-Stromlimit (PP), Hardware-Stromlimit.
- 🎚️ **Maximaler Ladestrom** (Register `0x0050`): Schieberegler, begrenzt durch das Hardware-Limit. `1–5 A` werden abgelehnt (unter dem IEC-61851-Minimum von 6 A).
- ▶️ **Schalter „Laden freigegeben“:** `aus` schreibt `0 A` (laut Spec gültig, verhindert das Laden), `ein` stellt den vorherigen Strom wieder her. *Das ist kein eigener Start/Stopp-Befehl der Wallbox – bitte mit angeschlossenem Auto prüfen, ob `0 A` das Laden bei deiner Firmware zuverlässig pausiert.*
- 🚀 **Boost-Schalter:** setzt den maximalen Ladestrom auf das Hardware-Limit und stellt beim Ausschalten den vorherigen Wert wieder her.
- 🔀 **Phasenumschaltung:** `Nur 1 Phase laden` (Coil `0x0003`). Wirkt nur bei Geräten, die 3↔1-phasig umschalten können; die Phase wird beim nächsten Übergang B2→C2 übernommen.
- 🚦 **Ladestation verfügbar** (Coil `0x0001`), 🔒 **Kabel dauerhaft verriegeln** (Coil `0x0006`), 🪪 **RFID-Authentifizierung** (Coil `0x000A`, neuere Firmware).
- 💡 **LED-Modus** (Register `0x0052`) und **LED-Helligkeit** (`0x0066`, neuere Firmware).
- ✅ **Schreib-Kontrolle:** Jeder Befehl wird zurückgelesen. Lehnt die Wallbox ihn ab oder nimmt sie ihn an, ohne den Wert zu übernehmen, zeigt Home Assistant einen Fehler, und das Log enthält `… geschrieben=…, zurückgelesen=…`.
- 🩺 **Diagnose:** Geräteinformationen (Hersteller, Produkt, Seriennummer, Firmware), Zugangskontrolle, Hardware-Konfiguration, RFID-Lesegerät, Buchse M2, Schlüsselschalter-Position und eine herunterladbare Diagnosedatei.

## 🔋 Energie-Dashboard & EMS

| Bedarf | Entity |
|---|---|
| Verbraucher im Energie-Dashboard | **Geladene Energie (gesamt)** – kWh, State-Class `total_increasing`, übersteht Neustarts |
| Leistung | **Ladeleistung gesamt** – gemessen, wenn die Wallbox einen Zähler hat, sonst **geschätzt** aus Phasenströmen × Spannung (230 V je Phase, wenn keine Spannung gemessen wird); das Attribut `estimated` zeigt den Fall |
| Stecker-Sensor | **Fahrzeug angeschlossen** (CP-Status A = nein, B/C = ja) |
| Lade-Sensor | **Lädt** (CP-Status C2 *und* mindestens 0,5 A) |
| Strom-Steuerung | **Maximaler Ladestrom** (Number) |
| Start / Stopp | **Laden freigegeben** (Schalter, `0 A` = Stopp) |
| Phasenumschaltung | **Nur 1 Phase laden** (Schalter) |

> **Genauigkeit:** *Geladene Energie (gesamt)* integriert die Ladeleistung über die Zeit. Ohne Zähler in der Wallbox ist das eine **Schätzung, kein geeichter Wert**; Lücken über zwei Minuten (z. B. Neustart von Home Assistant) werden nicht hochgerechnet. Bei Wallboxen mit Zähler und neuerer Firmware wird die gemessene Leistung verwendet.
>
> **Von der Wallbox nicht verfügbar:** Ladezustand (SOC) des Fahrzeugs (nutze die Integration deines Autos) und eine Auswahl „Lademodus / Force State“ (die Auswahl *LED-Modus* ändert nur die LED, **nicht** die Ladeleistung).

## 🚀 Installation

### Option 1: HACS Custom Repository
1. In Home Assistant **HACS → Integrationen** öffnen.
2. **⋮ → Benutzerdefinierte Repositories**, `https://github.com/Winkelhuf/ha-hager-witty-solar-modbus` als Typ **Integration** hinzufügen.
3. **Hager Witty Solar Wallbox** herunterladen und Home Assistant neu starten.

### Option 2: Manuell
1. `custom_components/witty_solar_wallbox` in dein `config/custom_components/`-Verzeichnis kopieren.
2. Home Assistant neu starten.

## ⚙️ Konfiguration

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen** → **„Hager Witty Solar Wallbox“** suchen.
2. **Host/IP**, **Port** (Standard `502`) und **Modbus-Unit-ID** (Standard `1`) eintragen.
3. Absenden. Der Verbindungstest liest das Magicbyte-Register (`0x0000`, erwartet `0xE3DC`).

**Voraussetzungen:** Das Kommunikationsboard der Wallbox ist im Netzwerk auf TCP-Port **502** erreichbar (am besten statische/reservierte IP), und Home Assistant ist **2025.12** oder neuer.

> [!IMPORTANT]
> **Nur einen Modbus-Client gleichzeitig verwenden.** Die Spezifikation sagt nicht, ob das Kommunikationsboard mehrere gleichzeitige TCP-Verbindungen unterstützt. Beende sicherheitshalber andere Modbus-Tools, andere Integrationen für dieselbe Wallbox und alte Test-Einträge, bevor du diese Integration einrichtest.

Die Integration fragt alle **10 Sekunden** ab und liest kleine Registerblöcke (in unseren Tests hat das Board die Verbindung bei einer Anfrage über 64 Register zurückgesetzt).

## 🛠️ Fehlersuche

| Problem | Lösung |
|---|---|
| *Connection reset by peer* / *Failed to connect* | Sicherstellen, dass kein anderer Modbus-Client verbunden ist, die Wallbox stromlos schalten und neu versuchen. |
| Entities erscheinen, sind aber *nicht verfügbar*, kein Gerät sichtbar | Browser hart neu laden (Strg+F5 / Cmd+Shift+R). Verwaiste Entities früherer Test-Einträge unter *Einstellungen → Geräte & Dienste → Entitäten* entfernen. |
| Viele Entities zeigen *unbekannt* | Vermutlich ältere Wallbox-Firmware, siehe *Benötigter Firmware-Stand* oben. |
| Eine Änderung wird „nicht übernommen“ | Die Wallbox hat den Schreibbefehl angenommen, aber den alten Wert behalten; Firmware und Log prüfen. |

Aktiviere für Fehlermeldungen das Debug-Logging und hänge das Log an dein Issue:

```yaml
logger:
  default: warning
  logs:
    custom_components.witty_solar_wallbox: debug
    pymodbus: debug
```

## 🚧 Bekannte Einschränkungen

- Noch nicht abgebildet: RFID-idTag-Feedback, Generic Blink/Farbe, Fallback-Werte für den Offline-Betrieb (`0x0051`, Coils `0x0002`/`0x0004`/`0x0009`), EV41-Compliance, DHCP-/Static-IP-Einstellungen, Firmware-/Konfigurations-Update.
- Pro Config-Eintrag wird eine Wallbox unterstützt; für mehrere Wallboxen die Integration je IP erneut hinzufügen.
- Geprüft an **einer** Wallbox mit Firmware `7.0.5.0/1.0.2.0`. Die Funktionen der neueren Firmware sind nach der Spezifikation umgesetzt und **noch nicht an echter Hardware getestet**. Abweichungen bitte als Issue melden, inklusive deiner Firmware-Version.

## 🧪 Entwicklung

```bash
pip install pytest pytest-homeassistant-custom-component pymodbus   # benötigt Python >= 3.14
pytest tests/ -v
```

GitHub Actions führt bei jedem Push und Pull Request **hassfest**, die **HACS-Validierung** und **pytest** aus. Siehe [CONTRIBUTING.md](CONTRIBUTING.md) und das [CHANGELOG](CHANGELOG.md).

## Mit KI entwickelt

Dieses Repository wurde mit erheblicher Unterstützung von KI-Coding-Assistenten (Gemini, Claude) entwickelt. Community-Integrationen können von umfangreicher KI-Unterstützung profitieren, wenn Review-Stand, Testumfang, Grenzen und Reife ehrlich kommuniziert werden. Diese Absicherungen verbessern die Nachvollziehbarkeit, garantieren aber keine Korrektheit.

**Teststand:** Automatisierte Tests decken Übersetzungen, Registertabellen und die Coordinator-Logik ab; die Integration wurde an einer echten Wallbox erprobt (siehe oben).

## Haftungsausschluss

Diese Integration steht in keiner Verbindung zu Hager und wird nicht von Hager unterstützt oder befürwortet. „Hager“ und „Witty“ sind Markenzeichen ihrer jeweiligen Inhaber. Die Steuerung einer Ladestation kann deine Elektroinstallation und dein Fahrzeug beeinflussen – Nutzung auf eigene Gefahr.

## 📜 Lizenz

MIT – siehe [LICENSE](LICENSE).
