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
# Verschiebung und/oder Rotation des Koordinatensystems in Bezug auf das Weltkoordinatensystem des Roboters.
task_frame = [0, 0, 0, 0, 0, 0]  #  Aufgabenspezifische Koordinatensystem 

# Bestimmt die Freiheitsgrade, in denen die Kraft angewandt wird. Hier ist nur die Z-Achse ausgewählt (dritter Eintrag).      
selection_vector = [0, 0, 1, 0, 0, 0]  

#  Diese Vektoren für den forceMode definieren die Kräfte/Momente,des Roboters
wrench_down = [0, 0, -10, 0, 0, 0]  # Abwärtskraft von `-10 N` entlang der Z-Achse
wrench_up   = [0, 0,  10, 0, 0, 0]  # Aufwärtskraft von `10 N` entlang der Z-Achse

# Modus der Kraftregelung: `2` steht häufig für eine Kraftsteuerung auf Basis von Kräften, die auf den Endeffektor wirken.
# 0 - Krafteinstellung linearer Achsen (Translation):
# 1 - Krafteinstellung sowohl linear als auch rotatorisch
# 2 - Impedanzregelung: Der Roboter verhält sich wie eine gefederte Masse in den ausgewählten Freiheitsgraden.
#     Hierbei werden Kräfte nicht direkt sondern proportional zu Positionsabweichungen umgesetzt. 
#     Dies sorgt für eine flexible Bewegung des Endeffektors, wenn eine externe Kraft ausgeübt wird
force_type = 2

# Setzt die maximal zulässigen Kräfte und Geschwindigkeiten für die Kraftregelung. 
# Hier sind die ersten drei Werte (Kräfte in N) und die letzten drei (Momente in Nm)
limits = [2, 2, 1.5, 1, 1, 1]

# Zeitintervall für die Steuerungsschleife setzen 
dt = 1.0/500  # 2ms

# Anfangsposition der Gelenke des Roboters.
joint_q = [-1.54, -1.83, -2.28, -0.59, 1.60, 0.023]
# Move to initial joint position with a regular moveJ
rtde_c.moveJ(joint_q)

# Execute 500Hz realtime control loop for 4 seconds, each cycle is 2ms
# -----------------------------------------------------------------------------
# Abhängig von i wird entweder eine nach unten oder eine nach oben gerichtete Kraft angewendet,
# um den Roboter in der entsprechenden Richtung zu bewegen.
# In Python erzeugt die Funktion `range(2000)` eine Sequenz von Zahlen, die bei 0 beginnt und bis zur Zahl 1999 reicht. 
# Die Schleife `for i in range(2000):` bedeutet damit, dass die Schleife 2000 Mal ausgeführt wird, 
# wobei `i` in jeder Iteration auf den nächsten ganzzahligen Wert in der Sequenz gesetzt wird. 
for i in range(2000):  # Schleife 2000mal ausführen i=0...1999
    # Zeitmessung initialisieren zur Überwachung der aktuellen Steuerperiode (hier 2 ms)
    t_start = rtde_c.initPeriod() # holt aktuelle Systemzeit / Zeitstempel
    # First move the robot down for 2 seconds, then up for 2 seconds
    if i > 1000:
        rtde_c.forceMode(task_frame, selection_vector, wrench_up, force_type, limits)
    else:
        rtde_c.forceMode(task_frame, selection_vector, wrench_down, force_type, limits)

    # Indem du `initPeriod()` am Anfang einer Steuerperiode und `waitPeriod(t_start)` am Ende aufrufst, 
    # kannst du die Ausführung so koordinieren, dass der Steuerungs-Loop mit konstanter Frequenz, hier genau alle 2 ms, ausgeführt wird.    
    rtde_c.waitPeriod(t_start) # Wartet auf Ablauf der Zeit t_start + dt 

# Zum Schluss wird der Kraftmodus beendet, und das Skript wird gestoppt, wodurch die Ausführung beendet wird.
rtde_c.forceModeStop()
rtde_c.stopScript()