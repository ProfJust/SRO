# Move a robot along a line given a start and end point by steps
# This macro shows three different ways of programming a robot using a Python script and the RoboDK API
# https://robodk.com/doc/en/PythonAPI/examples.html#points-to-program

# More information about the RoboDK API here:
# https://robodk.com/doc/en/RoboDK-API.html
# For more information visit:
# https://robodk.com/doc/en/PythonAPI/robodk.html#robolink-py

# Default parameters:
P_START = [ 450, -50, 400]  # Start point with respect to the robot base frame
P_END =   [ 400,  200, 500]  # End point with respect to the robot base frame
NUM_POINTS = 10  # Number of points to interpolate


# Function definition to create a list of points (line)
def MakePoints(xStart, xEnd, numPoints):
    """Generates a list of points"""
    if len(xStart) != 3 or len(xEnd) != 3:
        raise Exception("Start and end point must be 3-dimensional vectors")
    if numPoints < 2:
        raise Exception("At least two points are required")

    # Starting Points
    pt_list = []
    x = xStart[0]
    y = xStart[1]
    z = xStart[2]

    # How much we add/subtract between each interpolated point
    x_steps = (xEnd[0] - xStart[0]) / (numPoints - 1)
    y_steps = (xEnd[1] - xStart[1]) / (numPoints - 1)
    z_steps = (xEnd[2] - xStart[2]) / (numPoints - 1)

    # Incrementally add to each point until the end point is reached
    for i in range(numPoints):
        point_i = [x, y, z]  # create a point
        #append the point to the list
        pt_list.append(point_i)
        x = x + x_steps
        y = y + y_steps
        z = z + z_steps
    return pt_list


#---------------------------------------------------
#--------------- PROGRAM START ---------------------
from robodk.robolink import *  # API to communicate with RoboDK
from robodk.robomath import *  # basic matrix operations

# Generate the points curve path
POINTS = MakePoints(P_START, P_END, NUM_POINTS)

# Initialize the RoboDK API
RDK = Robolink()

# turn off auto rendering (faster)
RDK.Render(False)

# Automatically delete previously generated items (Auto tag)
list_names = RDK.ItemList()  # list all names
# for item_name in list_names:
    # if item_name.startswith('Auto'):
    #    RDK.Item(item_name).Delete()

# Promt the user to select a robot (if only one robot is available it will select that robot automatically)
robot = RDK.ItemUserPick('Select a robot', ITEM_TYPE_ROBOT)

# Turn rendering ON before starting the simulation
RDK.Render(True)

# Abort if the user hits Cancel
if not robot.Valid():
    quit()

# Retrieve the robot reference frame
reference = robot.Parent()

# Use the robot base frame as the active reference
robot.setPoseFrame(reference)

# get the current orientation of the robot (with respect to the active reference frame and tool frame)
pose_ref = robot.Pose()
print(Pose_2_TxyzRxyz(pose_ref))
# a pose can also be defined as xyzwpr / xyzABC
#pose_ref = TxyzRxyz_2_Pose([100,200,300,0,0,pi])# Type help("robodk.robolink") or help("robodk.robomath") for more information

#-------------------------------------------------------------
# Option 1: Move the robot using the Python script

# We can automatically force the "Create robot program" action using a RUNMODE state
# RDK.setRunMode(RUNMODE_MAKE_ROBOTPROG)

# Iterate through all the points
for i in range(NUM_POINTS):
    # update the reference target with the desired XYZ coordinates
    pose_i = pose_ref
    pose_i.setPos(POINTS[i])

    # Move the robot to that target:
    robot.MoveJ(pose_i)
    print("Going to Pose",pose_i)
    robot.Pause(2000)
    if i == 0:
        input("Start?")
    else:
        input("Weiter?")
   

# Done, stop program execution
print("Done")
quit()
