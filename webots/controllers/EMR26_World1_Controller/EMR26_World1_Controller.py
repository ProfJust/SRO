"""my_controller controller."""

from controller import Robot

robot = Robot()
timestep = int(robot.getBasicTimeStep())

# UR-Gelenke
ur_motors_0 = robot.getDevice("shoulder_lift_joint")
ur_sensor_0 = robot.getDevice("shoulder_lift_joint_sensor")
ur_sensor_0.enable(timestep)

ur_motors_1 = robot.getDevice("elbow_joint")

# Greifer
gripper = robot.getDevice("ROBOTIQ 2F-85 Gripper::left finger joint")
gripper_sensor = robot.getDevice("ROBOTIQ 2F-85 Gripper left finger joint sensor")
gripper_sensor.enable(timestep)

def clamp(x, xmin, xmax):
    return max(xmin, min(x, xmax))

cntr = 0

while robot.step(timestep) != -1:
    cntr += 1

    if cntr == 1:
        print("Pose 1")

        ur_motors_0.setPosition(-2.0)
        ur_motors_1.setPosition(-0.5)

        # Greifer schließen
        grip_target = clamp(0.8, 0.0, 0.8)
        gripper.setPosition(grip_target)

    if cntr == 50:
        # Sensorwerte erst nach einigen Schritten auslesen
        pos_value = ur_sensor_0.getValue()
        sensor_value = gripper_sensor.getValue()

        print("Pose 1 erreicht")
        print("ur_motor_0 auf Position", pos_value)
        print("Griffweite:", sensor_value)

    if cntr == 100:
        print("Pose 2")

        ur_motors_0.setPosition(0.0)

        # Greifer öffnen
        grip_target = clamp(0.01, 0.0, 0.8)
        gripper.setPosition(grip_target)

    if cntr == 150:
        pos_value = ur_sensor_0.getValue()
        sensor_value = gripper_sensor.getValue()

        print("Pose 2 erreicht")
        print("ur_motor_0 auf Position", pos_value)
        print("Griffweite:", sensor_value)