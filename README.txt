Anforderung an Verdampferprogramm
=================================

Was soll es können?
- Auslesen und Speichern der Flussraten
- Anzeigen der Flussratenentwicklung (I gegen t)
- Überwachen des Temperatur (falls T zu hoch I senken)
- Ausgasmodus: Hochregeln des Emissionsstroms (E gegen t) 
 + Muss zu unterbrechen sein: Flexibler Start / Pausieren des Hochfahrens / Stopp
- Userinterface: Verdampferkennzahlen (U, I, Emis, Flux, T)
 + Überwachen des Temperatur (falls T zu hoch I senken) -> Checkbox
 + Einstellen Parameter zum Hochfahren
 + Darstellen der Flussrate gegen Zeit (Plot)
 + Speicherort und Dateiformat wählen (Datei -> Speicher)

Was ist dazu notwendig? Programmteile:
- main -> Zusammensetzen der Einzelkomponenten
- EvapCom -> Kommunikation mit der Elektronik -> Fragt Werte von der Elektronik ab 
             und gibt diese zurück; (PySerial)
          -> Liest Werte ein um auf diese zu regeln
- Save data -> Speichert die Werte ab
- Read parameter -> Kommuniziert mit dem Nutzer (Abfragen von Werten; 
  Einlesen von Konfigurationen (Speicherort, Namen, Zeiten, etc.))
- Userinterface

Testen der Software / Mögliche Fehler:
- Was passiert, wenn die Kommunikation mit dem PC unterbrochen wird?
- Was passiert wenn man Manuell an den Reglern dreht?
- Nur sinnvolle Wertebereiche zulassen!
- !! Testen der Software an der Hardware !!


Evapcom -> Kommuniziert mit Elektronik
Data -> Speichert daten als Array
  -> add: fügt Wert hinzu
  -> save: Speichert array auf Platte (Leider zZ nur mit einem Wert)
UI -> Kommuniziert mit Nutzer
  -> Fragt ob Werte abgefragt werden sollen
  -> Fragt nach Zeitintervall
  -> Speichert Werte in data
  -> Fragt ob Werte auf HDD gespeichert werden sollen
