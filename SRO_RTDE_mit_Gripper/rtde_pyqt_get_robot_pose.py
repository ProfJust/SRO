# rtde_first_test.py
# Tested by OJ 12.11.24
# https://github.com/githubuser0xFFFF/py_robotiq_gripper/tree/master
# https://sdurobotics.gitlab.io/ur_rtde/examples/examples.html

# import rtde_control  # > pip install ur-rtde  ggf. pip iupdaten mit > python.exe -m pip install --upgrade pip
import rtde_receive
# import rtde_io
# import robotiq_gripper
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

        self.setMinimumSize(QSize(300, 200))    
        self.setWindowTitle("SRO ")
        self.btn_update_pose = QPushButton(' update TCP Pose ', self)
        self.btn_update_pose.clicked.connect(self.getTcpPoseSlot)
        self.btn_update_pose.resize(100,32)
        self.btn_update_pose.move(50, 50)      

        self.lbl_pose_x = QLabel(" x ", self)  
        self.lbl_pose_x.resize(30,20)       
        self.lbl_pose_x.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_pose_x.move(50, 100)

        self.lbl_pose_y = QLabel(" y ", self)  
        self.lbl_pose_y.resize(30,20)       
        self.lbl_pose_y.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_pose_y.move(50, 150)

        self.lbl_pose_z = QLabel(" z ", self)  
        self.lbl_pose_z.resize(30,20)       
        self.lbl_pose_z.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_pose_z.move(50, 200)

    def getTcpPoseSlot(self):
        print('Get Actual TcpPose from Robot')
        self.pose = self.rtde_r.getActualTCPPose() 
        # get actual Cartesian coordinates of the tool: (x,y,z,rx,ry,rz),
        # where rx, ry and rz is a rotation vector representation of the tool orientation """
        self.lbl_pose_x.setText('x: '+ str(self.pose[0]) )
        self.lbl_pose_x.setText('y: '+ str(self.pose[1]) )
        self.lbl_pose_x.setText('z: '+ str(self.pose[2]) )

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit( app.exec() )
