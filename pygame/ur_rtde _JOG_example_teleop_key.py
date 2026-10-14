# jog-example https://sdurobotics.gitlab.io/ur_rtde/examples/examples.html
# changed to Python
# Ziel => real UR3e per Tatstatur bewegen
# Last edited by Olaf Just at 11.05.2026
# tested with UR3e - Roboter 4

import rtde_control
import msvcrt
import time

# ROBOT_IP = "192.168.0.3"
ROBOT_IP = "192.168.0.17"  # UR3e - Roboter 4 
# ggf. IP-Adresse des UR-Roboters anpassen


rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)
speed_magnitude = 0.05
speed_vector = [0, 0, 0, 0, 0, 0]

try:
    # ## WARNING ###
    print("\a\a\a\a THIS SOFTWARE IS UNDER HEAVY CONSTRUCTION, /" 
          " USE WITH CAUTION! \a\a\a\a Press Enter to continue...")
    
    input("Pfeiltasten bewegen den Roboter,\n "
          "Space-Taste zum Stoppen der Bewegung...\n"
          "q zum Beenden... "
          "Verstanden? ")
    while True:
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'H':  # Up arrow
                speed_vector = [0, 0, -speed_magnitude, 0, 0, 0]
            elif key == b'P':  # Down arrow
                speed_vector = [0, 0, speed_magnitude, 0, 0, 0]
            elif key == b'K':  # Left arrow
                speed_vector = [speed_magnitude, 0, 0, 0, 0, 0]
            elif key == b'M':  # Right arrow
                speed_vector = [-speed_magnitude, 0, 0, 0, 0, 0]
            elif key == b'q':
                break
            else:
                speed_vector = [0, 0, 0, 0, 0, 0]
            rtde_c.jogStart(speed_vector, rtde_control.RTDEControlInterface.FEATURE_TOOL)
        time.sleep(0.02)
finally:
    rtde_c.jogStop()
    rtde_c.stopScript()
