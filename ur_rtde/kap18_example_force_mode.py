# UR3e - Force Mode
# Kraftregelung in negativer Z-Richtung

import time
import rtde_control
import rtde_receive

ROBOT_IP = "192.168.0.100"

rtde_c = rtde_control.RTDEControlInterface(
    ROBOT_IP, 500.0
)

rtde_r = rtde_receive.RTDEReceiveInterface(
    ROBOT_IP
)

# ----------------------------------------
# Parameter des Force Mode
# ----------------------------------------

task_frame = [0, 0, 0, 0, 0, 0]

selection_vector = [0, 0, 1, 0, 0, 0]

wrench = [0, 0, -10, 0, 0, 0]

force_type = 2

limits = [0.01, 0.01, 0.02, 0.1, 0.1, 0.1]

# Maximale Versuchsdauer
MAX_TIME = 5.0

# Maximaler Verfahrweg in Z: 30 mm
MAX_DISTANCE = 0.030

# Zusätzliche Kraftüberwachung
MAX_FORCE = 20.0

# ----------------------------------------
# Vorbereitung
# ----------------------------------------

input("Roboter in Startpose? ENTER zum Starten")

# Kraftsensor bei Stillstand und ohne Kontakt nullen
rtde_c.zeroFtSensor()

# Parameter des Kraftreglers
rtde_c.forceModeSetDamping(0.5)
rtde_c.forceModeSetGainScaling(0.5)

time.sleep(0.2)

start_pose = rtde_r.getActualTCPPose()
start_z = start_pose[2]

start_time = time.monotonic()
counter = 0

# ----------------------------------------
# Kraftregelung mit 500 Hz
# ----------------------------------------
try:
    while time.monotonic() - start_time < MAX_TIME:
        # Die Funktion time.monotonic() liefert den aktuellen Wert einer monotonen Uhr in Sekunden als Fließkommazahl.
        t_start = rtde_c.initPeriod()
        # Aktuelle TCP-Pose bestimmen
        pose = rtde_r.getActualTCPPose()
        # Aktuelle Kräfte und Momente
        force = rtde_r.getActualTCPForce()
        # Verfahrweg überwachen
        distance = abs(pose[2] - start_z)
        if distance >= MAX_DISTANCE:
            print("Maximaler Verfahrweg erreicht!")
            break

        # Kraftgrenze überwachen
        if abs(force[2]) >= MAX_FORCE:
            print("Maximale Z-Kraft erreicht!")
            break

        # Kraftmodus aktivieren bzw. aktualisieren
        ok = rtde_c.forceMode(
            task_frame,
            selection_vector,
            wrench,
            force_type,
            limits
        )

        if not ok:
            print("Force Mode fehlgeschlagen!")
            break

        # Ausgabe alle 100 ms
        if counter % 50 == 0:
            print(
                f"Fz = {force[2]:6.2f} N | "
                f"Z = {pose[2]*1000:7.2f} mm"
            )

        counter += 1
        # Zykluszeit von 2 ms einhalten
        rtde_c.waitPeriod(t_start)

except KeyboardInterrupt:
    print("Abbruch durch Benutzer")

finally:
    try:
        rtde_c.forceModeStop()
    finally:
        rtde_c.stopScript()

    print("Force Mode beendet")