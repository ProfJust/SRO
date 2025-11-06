# rtde_first_test.py
# Tested by OJ 12.11.24
# https://github.com/githubuser0xFFFF/py_robotiq_gripper/tree/master
# https://sdurobotics.gitlab.io/ur_rtde/examples/examples.html

import rtde_control  # > pip install ur-rtde  ggf. pip iupdaten mit > python.exe -m pip install --upgrade pip
import rtde_receive
import rtde_io
import robotiq_gripper

import time

ROBOT_IP = "192.168.0.3"
# ggf. WLAN deaktivieren

# RuntimeError: One of the RTDE input registers are already in use! Currently you must disable the EtherNet/IP adapter, PROFINET or any MODBUS unit configured on the robot. This might change in the future.
# ==>> Ethernet auf UR3e deaktivieren
def log_info(gripper):
    print(f"Pos: {str(gripper.get_current_position()): >3}  "
          f"Open: {gripper.is_open(): <2}  "
          f"Closed: {gripper.is_closed(): <2}  ")
    
def deg2rad(grad):
    return grad * 180.0 / 3.1415927


rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)
input("Roboter startet Bewegeung nach Eingabe beliebiger Taste")

"""rtde_receive_ = rtde_receive.RTDEReceiveInterface(ROBOT_IP)
input("lese Digitalen Ausgang Nr. 5")
if rtde_receive_.getDigitalOutState(5):
    print("Standard digital out (5) is HIGH")
else:
    print("Standard digital out (5) is LOW")"""

rtde_c.moveJ([deg2rad(-93.3), 
              deg2rad(-112.44),
              deg2rad(-102.71),
              deg2rad(-57.17),
              deg2rad(88.87),
              deg2rad(0.17)], 0.5, 0.3)

rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)
actual_q = rtde_r.getActualQ()  # in radian
print("Aktueller Zustand - Gelenkpositionen in Grad ")
for arg in actual_q:
    print(arg *180.0/3.1415927)




