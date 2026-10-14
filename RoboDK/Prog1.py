# Type help("robodk.robolink") or help("robodk.robomath") for more information
# Press F5 to run the script
# Documentation: https://robodk.com/doc/en/RoboDK-API.html
# Reference:     https://robodk.com/doc/en/PythonAPI/robodk.html
# Note: It is not required to keep a copy of this file, your Python script is saved with your RDK project

from robodk.robolink import *
from robodk.robomath import *

RDK = Robolink()

# Roboter holen
robot = RDK.Item('UR3e', ITEM_TYPE_ROBOT)

if not robot.Valid():
    raise Exception("Roboter 'UR3e' nicht gefunden")

# Geschwindigkeit
robot.setSpeed(100)

# Zwei Posen definieren
pose_1 = transl(300, -150, 300) * rotx(pi)
pose_2 = transl(300,  150, 300) * rotx(pi)  # Rotation um die X-Achse um pi 
""" pose = transl(...) * rotx(...)
    Pose = Position × Orientierung
    RoboDK erzeugt intern eine 4×4-Transformationsmatrix
    T =
    | R11 R12 R13 X |
    | R21 R22 R23 Y |
    | R31 R32 R33 Z |
    |  0   0   0  1 |
"""
# Startposition
robot.MoveJ([0, -90, 90, -90, -90, 0])

# Abwechselnd zwei Posen anfahren
for i in range(5):
    robot.MoveJ(pose_1)
    pause(1)

    robot.MoveJ(pose_2)
    pause(1)