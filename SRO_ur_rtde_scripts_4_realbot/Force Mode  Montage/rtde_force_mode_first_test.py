# rtde_montage_test.py
#----------------------------------------
# Erstes Testprogramm für Force Mode mit UR3e
# ---------------------------------------
# last edited by OJ 25.11.25
# Tested on UR3e
# Basierend auf dem Force-Mode-Exampe auf
# https://sdurobotics.gitlab.io/ur_rtde/examples/examples.html#forcemode-example

import rtde_control      # Steuerungsfunktionen des Roboters über RTDE
import rtde_receive
import math
ROBOT_IP = "192.168.0.3"   # IP des Roboters hier UR3e
rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)  # Verbindung herstellen
rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)

# Bezugsrahmen für die Kraftsteuerung setzen, in diesem Fall kein Offset (ein Null-Vektor).
# Verschiebung und/oder Rotation des Koordinatensystems in Bezug auf das Weltkoordinatensystem des Roboters.
task_frame = [0, 0, 0, 0, 0, 0]  #  Aufgabenspezifische Koordinatensystem 

# Bestimmt die Freiheitsgrade, in denen die Kraft angewandt wird. Hier ist nur die Z-Achse ausgewählt (dritter Eintrag).      
selection_vector = [1, 1, 1, 0, 0, 0]  

#  Diese Vektoren für den forceMode definieren die Kräfte/Momente,des Roboters
wrench_down = [ 1,  1, -10, 0, 0, 0]  # Abwärtskraft von `-1 N` entlang der Z-Achse
wrench_up   = [-1, -1, -10, 0, 0, 0]  # Aufwärtskraft von `1 N` entlang der Z-Achse

# Modus der Kraftregelung: `2` steht häufig für eine Kraftsteuerung auf Basis von Kräften, die auf den Endeffektor wirken.
# 0 - Krafteinstellung linearer Achsen (Translation):
# 1 - Krafteinstellung sowohl linear als auch rotatorisch
# 2 - Impedanzregelung: Der Roboter verhält sich wie eine gefederte Masse in den ausgewählten Freiheitsgraden.
#     Hierbei werden Kräfte nicht direkt sondern proportional zu Positionsabweichungen umgesetzt. 
#     Dies sorgt für eine flexible Bewegung des Endeffektors, wenn eine externe Kraft ausgeübt wird
force_type = 2

# Setzt die maximal zulässigen Kräfte und Geschwindigkeiten für die Kraftregelung. 
# Hier sind die ersten drei Werte (Kräfte in N) und die letzten drei (Momente in Nm)
limits = [1.0, 1.0, 1.0, 1, 1, 1]

# Zeitintervall für die Steuerungsschleife setzen 
dt = 1.0/500  # 2ms

# Anfangsposition der Gelenke des Roboters.
joint_q_rad = [1.2411526441574097, -0.7552269262126465, 0.858840290700094, -1.6968580685057582, -1.5734437147723597, -3.475983206425802]
print(" Joints in RAD ")
print(joint_q_rad)   
input("Roboter startet Bewegung nach Eingabe beliebiger Taste") 
rtde_c.moveJ(joint_q_rad, 0.5, 0.3)

input("Move Robot to Contact ?")
speed = [0, 0, -0.050, 0, 0, 0]
rtde_c.moveUntilContact(speed)

input("Move Robot Force Mode ?")

try:
    for i in range(200):  # Schleife 2000mal ausführen i=0...1999
        # Zeitmessung initialisieren zur Überwachung der aktuellen Steuerperiode (hier 2 ms)
        t_start = rtde_c.initPeriod() # holt aktuelle Systemzeit / Zeitstempel
        # First move the robot down for 2 seconds, then up for 2 seconds
        if i > 75:
        #    print(" forcemode up")
            rtde_c.forceMode(task_frame, selection_vector, wrench_up, force_type, limits)
        else:
        #    print(" forcemode down")
            rtde_c.forceMode(task_frame, selection_vector, wrench_down, force_type, limits)
        
        
        # Indem du `initPeriod()` am Anfang einer Steuerperiode und `waitPeriod(t_start)` am Ende aufrufst, 
        # kannst du die Ausführung so koordinieren, dass der Steuerungs-Loop mit konstanter Frequenz, hier genau alle 2 ms, ausgeführt wird.    
        rtde_c.waitPeriod(t_start) # Wartet auf Ablauf der Zeit t_start + dt 

    # Zum Schluss wird der Kraftmodus beendet, und das Skript wird gestoppt, wodurch die Ausführung beendet wird.
    rtde_c.forceModeStop()

    input("Move Robot up ?")
    # get actual pose
    pose = rtde_r.getActualTCPPose() 
    print("Pose ist :", pose)

    # Inverse Kinematic im Roboter
    rtde_c.moveL([pose[0], 
                pose[1],
                pose[2] + 0.05,
                pose[3],
                pose[4], 
                pose[5]], 0.1, 0.1)

   
    rtde_c.stopScript()
    print("\n Ende \n")


except KeyboardInterrupt:
    rtde_c.stopScript()

