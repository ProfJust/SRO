""" Erstes Python Programm zur Steuerung des simulierten Roboters in RoboDK
    OJ am 14.01.2026
    File: UR3e mit Robotiq First Test.rdk

    https://robodk.com/doc/en/PythonAPI/examples.html """

from robodk.robolink import Robolink   # import the robolink library (bridge with RoboDK)
from robodk.robomath import Pose_2_TxyzRxyz, pi, Mat, cos, sin  # import the robotics toolbox
# from robodk import robolink    # RoboDK API
# from robodk import robomath    # Robot toolbox
RDK = Robolink()                    # establish a link with the simulator
robot = RDK.Item('UR3e')      # retrieve the robot by name
if not robot.Valid():
    raise Exception('No robot selected or available')

# Pfad + Programm anzeigen
robot.setVisible(True)

# get the current position of the TCP with respect to the reference frame:
# (4x4 matrix representing position and orientation)
target_ref = robot.Pose()
pos_ref = target_ref.Pos()
print("Drawing a polygon around the target: ")
print(Pose_2_TxyzRxyz(target_ref))

# move the robot to the first point:
robot.MoveJ(target_ref)

# It is important to provide the reference frame and the tool frames when generating programs offline
robot.setPoseFrame(robot.PoseFrame())
robot.setPoseTool(robot.PoseTool())
robot.setRounding(10)  # Set the rounding parameter (Also known as: CNT, APO/C_DIS, ZoneData, Blending radius, cornering, ...)
robot.setSpeed(20)  # Set linear speed in mm/s

# Set the number of sides of the polygon:
n_sides = 6
R = 100

# make a hexagon around reference target:
for i in range(n_sides + 1):
    ang = i * 2 * pi / n_sides  #angle: 0, 60, 120, ...

    # -----------------------------
    # Movement relative to the reference frame
    # Create a copy of the target
    target_i = Mat(target_ref)
    pos_i = target_i.Pos()
    pos_i[0] = pos_i[0] + R * cos(ang)
    pos_i[1] = pos_i[1] + R * sin(ang)
    target_i.setPos(pos_i)
    print("Moving to target %i: angle %.1f" % (i, ang * 180 / pi))
    print(str(Pose_2_TxyzRxyz(target_i)))
    robot.MoveL(target_i)

    # -----------------------------
    # Post multiply: relative to the tool
    # target_i = target_ref * rotz(ang) * transl(R,0,0) * rotz(-ang)
    # robot.MoveL(target_i)

# move back to the center, then home:
robot.MoveL(target_ref)

print('Done')