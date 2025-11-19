"""THIS FILE IS UNDER HEAVY CONSTRUCTION

Ein Minimalkommando zur Kraftsteuerung in Z-Richtung:
Der Roboter drückt dabei 3 Sekunden lang mit ~1 N nach unten.

"""
from rtde_control import RTDEControlInterface
import time

rtde_c = RTDEControlInterface("192.168.0.10")

# Task Frame = TCP (0,0,0 Bezugsrahmen)
task_frame = [0, 0, 0, 0, 0, 0]

# Nur in Z kraftgeregelt
selection_vector = [0, 0, 1, 0, 0, 0]

# Kraft von -1N nach unten
wrench = [0, 0, -1, 0, 0, 0]  # eine konstante Kraft

# Force Type
force_type = 2

# Limits (Bewegungsbegrenzung)
limits = [0.1, 0.1, 0.1, 1, 1, 1]

rtde_c.forceMode(task_frame, selection_vector, wrench, force_type, limits)

time.sleep(3)   # Kraft für 3 Sekunden wirken lassen

rtde_c.forceModeStop()
rtde_c.stopScript()
