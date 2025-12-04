# rtde_montage_test.py
#----------------------------------------
# Erstes Testprogramm für Force Mode mit UR3e
# ---------------------------------------
# last edited by OJ 25.11.25
# Tested on UR3e
# Roboter fährt herunter bis Kontakt, 
# dann spiralförmige Bewegung im Kraftmodus
# Spiral tested with Wood 
# Dübel in OSB-Platte eindrücken

import rtde_control      # Steuerungsfunktionen des Roboters über RTDE
import rtde_receive
import time
import numpy as np
import math
ROBOT_IP = "192.168.0.17"   # IP des Roboters hier UR3e
rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)  # Verbindung herstellen
rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)

# Kraftsteuerung konfigurieren
task_frame = [0, 0, 0, 0, 0, 0]  
selection_vector = [0, 0, 1, 0, 0, 0]  # nur Z kraftgeregelt
wrench = [0, 0, -20, 0, 0, 0]          # 20 N nach unten
force_type = 2                         # „force“ Mode
# max. Abweichungen in den Freiheitsgraden
# Z‑Limit nicht zu groß wählen, damit der Roboter nicht weit „wegfedert“:
limits = [0.02, 0.02, 0.02, 0.2, 0.2, 0.2]  # 2 cm in Z

try:
    input("Move Robot to Contact ?")
    speed = [0, 0, -0.050, 0, 0, 0]
    rtde_c.moveUntilContact(speed)

    input("Move Robot Force Mode ?")
    rtde_c.forceMode(task_frame, selection_vector, wrench, force_type, limits)
    center = rtde_r.getActualTCPPose()      # [x, y, z, Rx, Ry, Rz]
    radius_step = 0.00002   # 0.1 mm pro Umdrehung
    angle_step  = 0.0008
    max_angle = 20 * 2 * 3.14159   # z.B. 20 Umdrehungen
    z_const = center[2]  # konstante Z-Höhe, Kraftregelung „federt“ Kontakt aus

    angle = 0.0  # Startwinkel
    while angle < max_angle:
        r = radius_step * angle
        dx = r * math.cos(angle)
        dy = r * math.sin(angle)

        target = center.copy()
        target[0] += dx
        target[1] += dy
        target[2] = z_const  # Z bleibt, Kraftregelung „federt“ Kontakt aus

        rtde_c.servoL(target,
              0.1,   # v_gain
              0.1,   # a_gain
              0.15,  # time
              0.15,  # lookahead_time
              100)    # gain !>=100      
        
        angle += angle_step

        # Abbruchbedingung: Prüfen, ob der Roboter sich weit genug in Z bewegt hat
        actualPose = rtde_r.getActualTCPPose()  
        movedZ = actualPose[2] - center[2] # Z-Achse bewegt?
        print(" moved Z = ", movedZ)
        if abs(movedZ) > 0.005:  # 2 mm Z-Bewegung abfangen
            rtde_c.servoStop(2.0)
            print(" Z limit reached, stopping force mode ")
            break

    # Ausführung beenden
    rtde_c.servoStop(2.0)
    rtde_c.forceModeStop()


    # Roboter anheben für weitere Tests
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
                pose[5]], 0.3, 0.1)
   
    rtde_c.stopScript()
    print("\n Ende \n")


except KeyboardInterrupt:
    rtde_c.stopScript()

except Exception as e:
    print("Exception occurred: ", e)
    rtde_c.stopScript()

