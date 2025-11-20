# rtde_pyqt_get_robot_pose.py
# Tested by OJ 27.11.24 on UR5e
# https://github.com/githubuser0xFFFF/py_robotiq_gripper/tree/master
# https://sdurobotics.gitlab.io/ur_rtde/examples/examples.html

# import rtde_control  # > pip install ur-rtde  ggf. pip iupdaten mit > python.exe -m pip install --upgrade pip
import rtde_receive
# import rtde_io
import robotiq_gripper
# import time

import sys
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtCore import QSize   
from PyQt6.QtWidgets import QPushButton 
from PyQt6.QtWidgets import QLabel

ROBOT_IP = "192.168.0.3"

class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)
        self.gripper = robotiq_gripper.RobotiqGripper()
        self.gripper.connect(ROBOT_IP, 63352)

        self.setMinimumSize(QSize(300, 300))    
        self.setWindowTitle("SRO -  get Robot Infos")
        self.pybutton = QPushButton(' update TCP Pose ', self)
        self.pybutton.clicked.connect(self.getTcpPoseSlot)
        self.pybutton.resize(150,32)
        self.pybutton.move(50, 50)      

        self.lbl_pose_x = QLabel(" x ", self)  
        self.lbl_pose_x.resize(150,20)       
        self.lbl_pose_x.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.lbl_pose_x.move(50, 100)

        self.lbl_pose_y = QLabel(" y ", self)  
        self.lbl_pose_y.resize(150,20)       
        self.lbl_pose_y.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.lbl_pose_y.move(50, 130)

        self.lbl_pose_z = QLabel(" z ", self)  
        self.lbl_pose_z.resize(150,20)       
        self.lbl_pose_z.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.lbl_pose_z.move(50, 160)

        self.lbl_gripper = QLabel("Gripper is ", self)  
        self.lbl_gripper.resize(250,20)       
        self.lbl_gripper.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.lbl_gripper.move(50, 190)

    def log_info(self ):
        print(f"Pos: {str(self.gripper.get_current_position()): >3}  "
              f"Open: {self.gripper.is_open(): <2}  "
              f"Closed: {self.gripper.is_closed(): <2}  ")


    def getTcpPoseSlot(self):
        print('Get Actual TcpPose from Robot')
        self.pose = self.rtde_r.getActualTCPPose() 
        # get actual Cartesian coordinates of the tool: (x,y,z,rx,ry,rz),
        # where rx, ry and rz is a rotation vector representation of the tool orientation """
        print(self.pose)
       # ui.lblStatus.setText( str(ui.spielZugNr)+'.Zug ')
        x = round(self.pose[0]*1000, 3) #  m => mm
        self.lbl_pose_x.setText('x: '+ str(x) + ' mm' )
        y = round(self.pose[1]*1000, 3)
        self.lbl_pose_y.setText('y: '+ str(y) + ' mm')
        z = round(self.pose[2]*1000, 3)
        self.lbl_pose_z.setText('z: '+ str(z) +' mm' )
        
        self.log_info()
        grpr_pos = self.gripper.get_current_position()
        # self.lbl_gripper.setText('Gripper: ' + str(grpr_pos))
        if grpr_pos < 10:
            self.lbl_gripper.setText('Gripper is open: ' + str(grpr_pos))
        else:
            self.lbl_gripper.setText('Gripper is closed: ' + str(grpr_pos))
   

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit( app.exec() )
