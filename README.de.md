# Hager Witty Modbus Integration für Home Assistant

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.12%2B-blue.svg)](https://www.home-assistant.io/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

🌐 English version: [README.md](README.md)

Lokale Home-Assistant-Integration für **Hager Witty (WittyPlus) Wallboxen**, die **nicht** Teil eines Hager-flow-Systems
sind, z. B. weil ein Energiemanager eines Drittanbieters sie steuert. Jede Wallbox wird **direkt über ihre IP-Adresse**
per **Modbus TCP** angesprochen – ohne Cloud und ohne Auto-Discovery. Umgesetzt ist die komplette Registertabelle aus dem
*WittyPlus ModbusTCP server developer's Guide v1.0.1*.

> Du suchst die Integration für Hager flow (XEM470) mit Auto-Discovery? Siehe
> [ha-hager-flow](https://github.com/Winkelhuf/ha-hager-flow).

---

## ⚠️ Bitte zuerst lesen

* **Nur eine Modbus-TCP-Verbindung.** Die Witty akzeptiert **eine einzige** TCP-Verbindung gleichzeitig. Wenn dein
  Energiemanager per Modbus TCP mit der Wallbox spricht, kann Home Assistant sich **nicht** gleichzeitig verbinden (und
  umgekehrt). Nutze dann für die gemeinsamen Daten die Home-Assistant-Integration des Energiemanagers oder trenne den
  anderen Client.
* **Modbus TCP zuerst aktivieren.** Es ist standardmäßig ausgeschaltet und wird in der **Hager-App** eingeschaltet.
* **Fallback-Werte.** Verschwindet der Modbus-Client (Link Down, TCP-Reset, Lese-/Schreib-Timeout), übernimmt die Wallbox
  ihre *Fallback*-Werte (Stromgrenze, Verfügbarkeit, Phasenmodus) – sofort oder nach 30 s (siehe *Fallback verzögern*).
  Stelle die Fallback-Entitäten auf Werte, mit denen du leben kannst. Home Assistant schreibt nur, wenn **du** eine
  Entität änderst oder einen Button drückst.
* **Noch nicht an echter Hardware getestet.** Die Registertabelle wurde anhand der Herstellerdokumentation umgesetzt.
  Bitte melde Auffälligkeiten (mit Debug-Log) – siehe [Bekannte offene Punkte](#-bekannte-offene-punkte).

---

## 📋 Voraussetzungen

* Hager WittyPlus Wallbox mit aktiviertem Modbus TCP, im Netzwerk erreichbar (**feste IP / DHCP-Reservierung empfohlen**).
* Port **502**, Modbus-Unit-Identifier **1** (Standard der Wallbox).
* Home Assistant **2025.12** oder neuer.

---

## 📊 Entitäten

Jede Wallbox wird **ein Gerät**. Namen und Statustexte richten sich nach deiner Home-Assistant-Sprache (Deutsch / English).

### Sensoren
| Entität | Register | Hinweis |
|---|---|---|
| **Status** | `0x302B` | Zustand der Wallbox im Klartext (Bereit, Wartet auf …, Lädt (Solar), Fehler …) |
| **Control-Pilot-Zustand** | `0x3008` | A1 … F nach DIN EN 61851 |
| **Leistung**, **Leistung L1/L2/L3** | `0x3013`, `0x3010-12` | W |
| **Strom L1/L2/L3** | `0x300A-0C` | A (`0x7FFF` = ungültig → nicht verfügbar) |
| **Spannung L1/L2/L3** | `0x300D-0F` | V |
| **Energie aktuelle Session** | `0x5000` | Wh → kWh, `total_increasing` (startet mit jeder Session neu) |
| **Energie gesamt** | *berechnet* | Dauerhaft steigender kWh-Zähler für das **Energie-Dashboard** (summiert die Session-Energie, bleibt über Neustarts erhalten) |
| **Ladedauer** | `0x500A` | Zeit im Zustand C |
| **Session-Start / -Ende** | `0x5002`, `0x5006` | Zeitstempel |
| **Session-Badge**, **Session-Badge-Typ**, **Letzter Stoppgrund** | `0x500C-0x5013` | Stoppgrund im Klartext |
| **Session-Zustand** | `0x5014` | Keine Session / Läuft / Beendet |
| **Kabelverriegelung** | `0x3025` | Entriegelt, verriegelt, fest angeschlagen, blockiert … |
| Diagnose: **PWM-Tastverhältnis**, **Hardware-Stromgrenze**, **Kabel-Stromgrenze**, **Wallbox-Uhrzeit**\*, **Letzter RFID-Tag**\* | | \*standardmäßig deaktiviert |

### Binärsensoren
**Lädt**, **Fahrzeug verbunden**, **Fehler** (aus Status / Control Pilot abgeleitet), **Uhrzeit gesetzt** (Diagnose).

### Steuerung
| Entität | Register | Hinweis |
|---|---|---|
| **Maximaler Ladestrom** (Number, 0–32 A) | `0x301E` | Der Wert, den ein Energiemanager setzen würde. PWM-Auflösung der Wallbox: 0,6 A. |
| **Maximaler Ladestrom (Fallback)** (Number) | `0x301F` | Gilt, wenn der Modbus-Client verloren geht |
| **Phasenumschaltung** (Select: *3 Phasen* / *Nur 1 Phase*) | `0x3022` | **Umschaltung 1-phasig ↔ 3-phasig** |
| **Phasenumschaltung (Fallback)** (Select) | `0x3023` | |
| **Verfügbar** (Schalter) | `0x3020` | Aus = Wallbox gesperrt (Bedienteil rot) |
| **Verfügbar (Fallback)** (Schalter) | `0x3021` | |
| **Fallback 30 s verzögern** (Schalter) | `0x3026` | |
| **Uhrzeit synchronisieren** (Button) | `0x3000` | Schreibt die aktuelle UTC-Zeit in die Wallbox |
| **RFID-Rückmeldung**\* (Select) | `0x400B` | Antwort auf einen vorgehaltenen RFID-Tag – standardmäßig deaktiviert |

Die **RFID-Register** sind optional: Sie werden nur bei aktiver RFID-Authentifizierung bedient. Lehnt die Wallbox sie ab,
werden sie übersprungen und alle 5 Minuten neu versucht – ohne Log-Flut. Jeder andere abgelehnte Block wird einmalig als
Warnung protokolliert.

### Energie-Dashboard
Die Wallbox meldet nur die Energie der **aktuellen** Session (startet bei jeder neuen Session bei 0). **Energie gesamt**
summiert die Zuwächse dieses Registers und zählt über Sessions hinweg korrekt weiter. Damit kannst du sie unter
**Einstellungen → Dashboards → Energie** als *einzelnes Gerät* hinzufügen. Der Zählerstand wird nach Neustarts
wiederhergestellt.

Einschränkung: Beginnt eine neue Session, während Home Assistant offline ist, und wurde darin bereits *mehr* geladen als
der letzte bekannte Wert der vorigen Session, wird nur die Differenz gezählt. Das betrifft nur lange Abfragelücken.

---

## 🚀 Installation

### HACS – benutzerdefiniertes Repository
1. **HACS → ⋮ → Benutzerdefinierte Repositories**
2. Repository: `https://github.com/Winkelhuf/ha-hager-witty`, Typ **Integration** → **Hinzufügen**
3. **Hager Witty Modbus** herunterladen und Home Assistant **neu starten**.

### Manuell
`custom_components/hager_witty/` nach `<config>/custom_components/` kopieren und neu starten.

### Updates
Ein **GitHub-Release mit Versions-Tag** veröffentlichen (z. B. `v0.1.1`) und `version` in
`custom_components/hager_witty/manifest.json` (sowie `VERSION` in `const.py`) erhöhen – HACS erkennt Updates anhand der Releases.

---

## ⚙️ Einrichtung

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen → „Hager Witty Modbus“**
2. **IP-Adresse**, einen **Namen** (z. B. *Witty Garage*), Port (502) und Unit-ID (1) eintragen.
3. Für jede Wallbox wiederholen (jede hat ihre eigene IP; dieselbe IP kann nicht doppelt hinzugefügt werden).

* **Optionen** (Zahnrad): Abfrageintervall, Standard 5 s (2–60 s).
* **Neu konfigurieren** (⋮-Menü des Eintrags): IP/Port nach einem Routerwechsel ändern – die Wallbox wird an ihrer Kennung erkannt.

---

## 🧭 Bekannte offene Punkte

Die Herstellerdokumentation ist an einigen Stellen mehrdeutig. So interpretiert die Integration sie – bitte melde, falls
sich deine Wallbox anders verhält:

1. **Adressen sind hexadezimal** (`301E` = 12318) und werden ohne Offset als Protokolladresse verwendet.
2. **Mehrregister-Werte** (uint32/int32/uint64/Zeitstempel) nutzen die Standard-Modbus-Wortreihenfolge, höchstwertiges Wort zuerst.
3. **Ungültiger Strom** ist `0x7FFF` (die Doku nennt `0x7FFFF` bei einem 16-Bit-Register).
4. **Session-Energie (`0x5000`)** wird als uint32 in **Wh** gelesen, **Ladedauer (`0x500A`)** als uint32 in Sekunden.
5. **Control-Pilot-Zustand (`0x3008`)** wird als 2-Zeichen-ASCII-Text in einem Register gelesen.
6. **Session-Badge** (`0x500C/0x500D`) und RFID-Tag (`0x4001/0x4002`) werden als Hex-UID angezeigt.

---

## 🛠️ Technik

Asynchrones `pymodbus` (3.11+), eine dauerhafte, per Lock geschützte Verbindung (die Wallbox erlaubt nur eine), das
`DataUpdateCoordinator`-Muster mit **8 zusammenhängenden Blocklesungen pro Abruf** (keine undokumentierten Adressen),
übersetzte Entitätsnamen und -zustände, Config-, Options- und Reconfigure-Flow sowie GitHub Actions für **hassfest**,
**HACS** und **pytest**. Die Registertabelle liegt in `registers.py` ohne Home-Assistant-Importe und ist durch Unit-Tests abgedeckt.

---

## Mit KI entwickelt

Dieses Repository wurde mit erheblicher Unterstützung eines KI-Assistenten (Claude) entwickelt, auf Basis der Struktur der
Integration [ha-hager-flow](https://github.com/Winkelhuf/ha-hager-flow). Die Register-Interpretation ist durch Unit-Tests
abgesichert, die Integration wurde aber **noch nicht an einer echten Wallbox getestet**.

## Haftungsausschluss

Nicht mit Hager verbunden oder von Hager unterstützt. „hager“ und „Witty“ sind Marken der jeweiligen Inhaber. Schreibzugriffe
auf eine Ladestation können das Ladeverhalten beeinflussen – Nutzung auf eigene Gefahr.

## 📜 Lizenz

MIT – siehe [LICENSE](LICENSE).
