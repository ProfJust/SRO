# rtde_montage_test.py
#----------------------------------------
# Montage eines Lego-Duplo-Turms
# ---------------------------------------
# last edited by OJ 6.12.24
# to be Tested 4 on UR5e
# Basierend auf dem Force-Mode-Exampe auf
# https://sdurobotics.gitlab.io/ur_rtde/examples/examples.html#forcemode-example


import rtde_control      # Steuerungsfunktionen des Roboters über RTDE
ROBOT_IP = "127.0.0.1"   # IP des Roboters
rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)  # Verbindung herstellen

# Bezugsrahmen für die Kraftsteuerung setzen, in diesem Fall kein Offset (ein Null-Vektor).
task_frame = [0, 0, 0, 0, 0, 0]  
# Bestimmt die Freiheitsgrade, in denen die Kraft angewandt wird. Hier ist nur die Z-Achse ausgewählt (dritter Eintrag).      
selection_vector = [0, 0, 1, 0, 0, 0]  
#  Diese Vektoren definieren die Kräfte/Momente, die auf den Roboter wirken.
#  In diesem Fall wird zunächst eine Abwärtskraft von `-10 N` und später eine Aufwärtskraft von `10 N` entlang der Z-Achse angewendet.
wrench_down = [0, 0, -10, 0, 0, 0]
wrench_up = [0, 0, 10, 0, 0, 0]

# Modus der Kraftregelung: `2` steht häufig für eine Kraftsteuerung auf Basis von Kräften, die auf den Endeffektor wirken.
force_type = 2
# Setzt die maximal zulässigen Kräfte und Geschwindigkeiten für die Kraftregelung. 
# Hier sind die ersten drei Werte (Kräfte) und die letzten drei (Momente)
limits = [2, 2, 1.5, 1, 1, 1]

# Zeitintervall für die Steuerungsschleife (2 ms)
dt = 1.0/500  # 2ms

# Anfangsposition der Gelenke des Roboters.
joint_q = [-1.54, -1.83, -2.28, -0.59, 1.60, 0.023]
# Move to initial joint position with a regular moveJ
rtde_c.moveJ(joint_q)

# Execute 500Hz control loop for 4 seconds, each cycle is 2ms
# Abhängig von i wird entweder eine nach unten oder eine nach oben gerichtete Kraft angewendet,
# um den Roboter in der entsprechenden Richtung zu bewegen.
for i in range(2000):  # woher kommt i???
    t_start = rtde_c.initPeriod()
    # First move the robot down for 2 seconds, then up for 2 seconds
    if i > 1000:
        rtde_c.forceMode(task_frame, selection_vector, wrench_up, force_type, limits)
    else:
        rtde_c.forceMode(task_frame, selection_vector, wrench_down, force_type, limits)
    rtde_c.waitPeriod(t_start)

# Zum Schluss wird der Kraftmodus beendet, und das Skript wird gestoppt, wodurch die Ausführung beendet wird.
rtde_c.forceModeStop()
rtde_c.stopScript()