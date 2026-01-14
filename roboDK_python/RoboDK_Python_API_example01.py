from robodk.robolink import Robolink       # import the robolink library (bridge with RoboDK)
from robodk.robomath import transl      # import the robotics toolbox
RDK = Robolink()                    # establish a link with the simulator
robot = RDK.Item('UR3e')      # retrieve the robot by name
robot.setJoints([0, 0, 0, 0, 0, 0])      # set all robot axes to zero

target = RDK.Item('Target 3')         # retrieve the Target item
robot.MoveJ(target)                 # move the robot to the target
robot.Pause(2000)
# calculate a new approach position 100 mm along the Z axis of the tool with respect to the target


approach = target.Pose() * transl(0, 0, +100)
robot.MoveL(approach) 
input("Weiter?")              # linear move to the approach position
robot.Pause(2000)
approach2 = target.Pose() * transl(0, 100, 0)
robot.MoveL(approach2)

