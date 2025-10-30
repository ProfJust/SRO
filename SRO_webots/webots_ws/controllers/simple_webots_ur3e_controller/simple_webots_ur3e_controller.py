"""simple_webots_controller"""

# Webots Controller, in Roboter einbinden
# ------------------------------------------------
# OJ 21.10.25
# Grundlegende Bewegungen im Webots UR3e
# -----------------------------------------------
# You may need to import some classes of the controller module. Ex:
#  from controller import Robot, Motor, DistanceSensor
from controller import Robot

# create the Robot instance.
robot = Robot()
#sensor = Sensor()

# get the time step of the current world.
timestep = int(robot.getBasicTimeStep())

"""
aus Proto File 
shoulder_pan_joint
shoulder_lift_joint
elbow_joint
wrist_1_joint
wrist_2_joint
wrist_3_joint
"""
ur_motors_0 = robot.getDevice("shoulder_lift_joint")

ur_sensors_0 = robot.getDevice("shoulder_lift_joint_sensor")
ur_sensors_0.enable(timestep)

ur_motors_1 = robot.getDevice("elbow_joint")

gripper = robot.getDevice("ROBOTIQ 2F-85 Gripper::left finger joint")
gripper_sensor = robot.getDevice("ROBOTIQ 2F-85 Gripper left finger joint sensor")
gripper_sensor.enable(timestep)

#grpr_left_finger = robot.getDevice("ROBOTIQ 2F-85_gripper_left_finger_joint");
#grpr_left_finger = robot.getDevice("finger_1_joint_1")
#ur_motors_0.enable(timestep)
"""
ur_motors[1] = robot.getDevice("elbow_joint");
ur_motors[1].enable(timestep)
ur_motors[2] = robot.getDevice("wrist_1_joint");
ur_motors[2].enable(timestep)
ur_motors[3] = robot.getDevice("wrist_2_joint");
ur_motors[3].enable(timestep)"""
  

# Main loop:
# - perform simulation steps until Webots is stopping the controller
cntr = 0
while robot.step(timestep) != -1:
    # Read the sensors:
    # Enter here functions to read sensor data, like:
    #  val = ds.getValue()

    # Process sensor data here.

    # Enter here functions to send actuator commands, like:
   cntr = cntr +1
   if cntr==1:
       print("Pose 1")
       ur_motors_0.setPosition(-2.0)
       pos_value = ur_sensors_0.getValue()
       print("ur_motor_0 auf Position", pos_value)
       
       ur_motors_1.setPosition(-0.5)
       
       # Enable the gripper
       gripper.setPosition(0.8)  # Fully close 
       sensor_value = gripper_sensor.getValue()
       print("Griffweite:",sensor_value)
       #print(f"Griffweite:: {sensor_value}")
   if cntr==100:
       print("Pose 2")
       ur_motors_0.setPosition(0.0)
       print("ur_motor_0 auf Position", pos_value)
       # Example: Close the gripper
       gripper.setPosition(0.01)  # Fully opened
       sensor_value = gripper_sensor.getValue()
       print("Griffweite:",sensor_value)

# Enter here exit cleanup code.
