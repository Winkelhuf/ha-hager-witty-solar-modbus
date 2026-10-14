## 🇩🇪 Deutsche Dokumentation

Diese Home-Assistant-Custom-Component ermöglicht die lokale Anbindung und Steuerung der **Hager Witty Solar** Wallbox über Modbus TCP (basierend auf der offiziellen Modbus-Spezifikation v0.28).

### Funktionen
* **Sensoren:** Live-Werte für Spannung, Strom und Leistung je Phase, Control-Pilot-Zustand (CP State), PWM-Wert, Energiezähler der Ladesitzung (Wh), RFID-Chip-UID und Fehlercodes.
* **Schalter (Coils):** Station freigeben/sperren (HMI), 1-Phasen-Modus erzwingen (`Switch3to1`), RFID-Authentifizierung ein-/ausschalten sowie EV41-Konformität.
* **Regler (Number Entities):** Maximaler Ladestrom, Ladestrom-Fallback bei Verbindungsverlust und LED-Helligkeit einstellen.
* **Config Flow:** Komfortable Einrichtung direkt über die Home-Assistant-Benutzeroberfläche (ohne `configuration.yaml`).

### Installation über HACS (Empfohlen)
1. Öffne HACS in deinem Home Assistant.
2. Gehe auf **Integrationen**, klicke oben rechts auf die drei Punkte und wähle **Benutzerdefinierte Repositories**.
3. Füge die Repository-URL `https://github.com/Winkelhuf/ha-hager-witty-solar-modbus` ein und wähle als Kategorie **Integration**.
4. Klicke auf **Installieren** bei der Integration "Hager Witty Solar EVCS".
5. Starte Home Assistant neu.

### Einrichtung
1. Gehe in Home Assistant auf **Einstellungen** -> **Geräte & Dienste** -> **Integration hinzufügen**.
2. Suche nach **Hager Witty Solar**.
3. Gib die IP-Adresse deiner Wallbox und den Modbus-Port (Standard: `502`) ein.

---

### License / Lizenz
This project is licensed under the [MIT License](LICENSE).