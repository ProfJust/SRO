# Dieses Python-Skript steuert einen Universal Robots (UR)-Roboter über die rtde_control-Bibliothek.
# Es ermöglicht die manuelle Bewegung des Roboterwerkzeugs (Tool) mithilfe der Pfeiltasten auf der Tastatur.

#  Dazu nutzen wir die ur_rtde JOG- Funktion (kontinuierliche Bewegung mit konstanter Geschwindigkeit).
# jogStart() startet die "Jogging"-Bewegung 
# https://sdurobotics.gitlab.io/ur_rtde/examples/examples.html#jog-example

# Last edited by Olaf Just at 19.05.2025
# Tested on UR5e 
#--------------------------------------------------------------------------------
import rtde_control
import msvcrt
import time

ROBOT_IP = "192.168.0.3"
rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)

# TCP soll bewegt werden
speed_magnitude = 0.03  # Geschwindigkeit in m/s
# Die Roboterbewegung wird als 6D-Vektor definiert (3 lineare + 3 rotatorische Achsen).
speed_vector = [0, 0, 0, 0, 0, 0] # [x, y, z, rx, ry, rz]

input(" Roboter TCP mit Pfeiltasten bewegen, q => STOP, <weiter mit ENTER> ")
try:
    while True:
        speed_vector = [0, 0, 0, 0, 0, 0]  # Stopp
        if msvcrt.kbhit():  # Prüft, ob eine Taste gedrückt wurde
            key = msvcrt.getch()  # Liest die Taste
            if key == b'\xe0':
                key = msvcrt.getch()
                if key == b'H':  # Pfeil-oben
                    speed_vector = [0, 0, speed_magnitude, 0, 0, 0]
                elif key == b'P':  # Pfeil-unten
                    speed_vector = [0, 0, -speed_magnitude, 0, 0, 0]
                elif key == b'K':  # Pfeil-links
                    speed_vector = [speed_magnitude, 0, 0, 0, 0, 0]
                elif key == b'M':  # Pfeil-rechts
                    speed_vector = [-speed_magnitude, 0, 0, 0, 0, 0]
            elif key == b'q':  # Beenden der Schleife => jogStop (s.u.)
                    break
            elif key == b' ':  # Beenden der Schleife => jogStop (s.u.)
                    break
            #else:
               

        # rtde_c.jogStart(speed_vector, rtde_control.RTDEControlInterface.FEATURE_TOOL) 
        # startet die "Jogging"-Bewegung (kontinuierliche Bewegung mit konstanter Geschwindigkeit).
        ### **Der Parameter `FEATURE_TOOL`**
        # FEATURE_TOOL bedeutet, dass die Bewegung relativ zum Werkzeugkoordinatensystem erfolgt.
        #   Mit `rtde_control.RTDEControlInterface.FEATURE_TOOL` wird festgelegt, dass sich die Bewegung **relativ zum Tool-Koordinatensystem** (Werkzeugorientierung) verhält.  
        # **Alternative Optionen:**  
        # - `FEATURE_BASE`: Bewegung relativ zum Basiskoordinatensystem (Roboterfuß).  
        # - `FEATURE_MOMENTARY_MOVEMENT`: Bewegung relativ zur aktuellen Position.

        rtde_c.jogStart(speed_vector, rtde_control.RTDEControlInterface.FEATURE_BASE) 

        time.sleep(0.02)  # 20 ms Wartezeit
finally:
    rtde_c.jogStop()
    rtde_c.stopScript()


"""
## **Erklärung von `jogStart()` und dem Geschwindigkeitsvektor `[x, y, z, rx, ry, rz]`**

### **Was macht `jogStart()`?**
`jogStart()` ist eine Methode der `RTDEControlInterface`-Bibliothek für **Universal Robots (UR)**. Sie startet eine *Jogging-Bewegung* – also eine kontinuierliche Bewegung des Roboter-Tools (Werkzeugs) mit einer konstanten Geschwindigkeit in einer bestimmten Richtung.  
**Wichtig:**  
- Der Roboter bewegt sich so lange, bis `jogStop()` aufgerufen wird.  
- Jogging wird oft für manuelle Steuerung (z.B. Teach-In) genutzt.

---

### **Der Geschwindigkeitsvektor `[x, y, z, rx, ry, rz]`**
Der Vektor definiert die **Bewegungsrichtung und -geschwindigkeit** in 6 Dimensionen:
1. **Lineare Geschwindigkeiten** (in m/s):
   - `x`: Bewegung vor/rück (Tool-X-Achse)
   - `y`: Bewegung links/rechts (Tool-Y-Achse)
   - `z`: Bewegung auf/ab (Tool-Z-Achse)
2. **Rotatorische Geschwindigkeiten** (in rad/s):
   - `rx`: Drehung um die Tool-X-Achse (Roll)
   - `ry`: Drehung um die Tool-Y-Achse (Pitch)
   - `rz`: Drehung um die Tool-Z-Achse (Yaw)

**Beispiel:**  
- `[0.1, 0, 0, 0, 0, 0]` → Tool bewegt sich mit 0.1 m/s entlang seiner eigenen X-Achse.  
- `[0, 0, 0, 0, 0, 0.5]` → Tool dreht sich mit 0.5 rad/s um seine eigene Z-Achse.

---

### **Der Parameter `FEATURE_TOOL`**
Mit `rtde_control.RTDEControlInterface.FEATURE_TOOL` wird festgelegt, dass sich die Bewegung **relativ zum Tool-Koordinatensystem** (Werkzeugorientierung) verhält.  
**Alternative Optionen:**  
- `FEATURE_BASE`: Bewegung relativ zum Basiskoordinatensystem (Roboterfuß).  
- `FEATURE_MOMENTARY_MOVEMENT`: Bewegung relativ zur aktuellen Position.

**Praxis-Tipp:**  
Bei `FEATURE_TOOL` hängt die Richtung der Bewegung von der aktuellen Ausrichtung des Tools ab. Wenn das Tool z.B. um 90 Grad gedreht ist, entspricht die Tool-X-Achse der Base-Y-Achse.

---

## **Wichtige Hinweise**
1. **Sicherheit:**  
   - Jogging-Bewegungen sind potentiell gefährlich, da der Roboter *kontinuierlich* läuft.  
   - Immer einen Not-Aus in Reichweite haben und mit niedrigen Geschwindigkeiten testen (z.B. `speed_magnitude = 0.05`).

2. **Koordinatensystem überprüfen:**  
   - Die Richtungen `x/y/z` beziehen sich auf das Tool, nicht auf die Weltkoordinaten.  
   - Nutze die UR-Polyscope-Oberfläche, um die Tool-Orientierung zu visualisieren.

3. **Fehler im Code:**  
   In deinem Skript fehlt die korrekte Behandlung der Pfeiltasten-Erkennung unter Windows (siehe vorherige Antwort). Ohne diese Korrektur reagiert das Skript nicht auf die Pfeiltasten.

---

## **Zusammenfassung**  
- `jogStart()` startet eine Roboterbewegung mit konstanter Geschwindigkeit.  
- Der Vektor `[x, y, z, rx, ry, rz]` legt Richtung und Geschwindigkeit fest.  
- `FEATURE_TOOL` bedeutet: Die Bewegung erfolgt relativ zur aktuellen Werkzeugorientierung.  
- **Teste den Code immer im Schrittmodus des Roboters und mit reduzierter Geschwindigkeit!**

---
Antwort von Perplexity: pplx.ai/share





Joystick-Integration (Pseudocode)
# Annahme: Joystick liefert Werte zwischen -1 und 1 für jede Achse
joystick_x = 0.5  # Beispielwert vom Joystick
joystick_z = -0.3

speed_x = joystick_x * 0.2  # Max 0.2 m/s
speed_z = joystick_z * 0.1  # Max 0.1 m/s

rtde_c.jogStart([speed_x, 0, speed_z, 0, 0, 0], rtde_control.FEATURE_TOOL)
"""