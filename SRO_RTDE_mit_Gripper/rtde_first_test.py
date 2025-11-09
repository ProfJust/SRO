# rtde_first_test.py
# Tested by OJ 6.11.25
# https://github.com/githubuser0xFFFF/py_robotiq_gripper/tree/master
# https://sdurobotics.gitlab.io/ur_rtde/examples/examples.html

import rtde_control  # > pip install ur-rtde  ggf. pip iupdaten mit > python.exe -m pip install --upgrade pip
import rtde_receive
import rtde_io
import robotiq_gripper

import time

ROBOT_IP = "192.168.0.11"
def log_info(gripper):
    print(f"Pos: {str(gripper.get_current_position()): >3}  "
          f"Open: {gripper.is_open(): <2}  "
          f"Closed: {gripper.is_closed(): <2}  ")
    
def gripper_first_test():
    print("Creating gripper...")
    gripper = robotiq_gripper.RobotiqGripper()
    print("Connecting to gripper...")
    gripper.connect(ROBOT_IP, 63352)
    print("Activating gripper...")
    gripper.activate()

    gripper.move_and_wait_for_pos(255, 255, 255)
    log_info(gripper)
    gripper.move_and_wait_for_pos(0, 255, 255)
    log_info(gripper)

def deg2rad(grad):
    return grad * 180.0 / 3.1415927


# ---- main ----
if __name__ == '__main__':
    input("Gripper startet Bewegeung nach Eingabe beliebiger Taste")
    gripper_first_test()

    rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)
    actual_q = rtde_r.getActualQ()  # in radian
    print("Aktueller Zustand - Gelenkpositionen in Grad ")
    for arg in actual_q:
        print(arg *180.0/3.1415927)
    
    input("Roboter startet Bewegung nach Eingabe beliebiger Taste")
    rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)
    
    new_q = actual_q
    print(new_q)
    new_q[0] = new_q[0] - 1  # Änderung Gelenk[0] = Base 
    print(new_q)
    rtde_c.moveJ(new_q, 0.5, 0.3)

    new_q = actual_q
    print(new_q)
    new_q[0] = new_q[0] + 1  # Änderung Gelenk[0] = Base 
    print(new_q)
    rtde_c.moveJ(new_q, 0.5, 0.3)


    # input("setze Digitalen Ausgang Nr. 7")
    # rtde_io = rtde_io.RTDEIOInterface(ROBOT_IP)
    # rtde_io.setStandardDigitalOut(7, True)
    # rtde_io.setToolDigitalOut(0, True)
    # time.sleep(2) # Delay for 2 seconds
    # rtde_io.setStandardDigitalOut(7, False)
    # time.sleep(2) # Delay for 2 seconds

    # rtde_receive_ = rtde_receive.RTDEReceiveInterface(ROBOT_IP)
    # input("lese Digitalen Ausgang Nr. 5")
    # if rtde_receive_.getDigitalOutState(5):
    #     print("Standard digital out (5) is HIGH")
    # else:
    #     print("Standard digital out (5) is LOW")


