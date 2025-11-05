# rtde_pyqt_robot_gui2.py
# --------------------------------
# Last tested by OJ 18.12.24 on UR5e
# GUI vor real Universal Robot using ur_rtde
# https://github.com/githubuser0xFFFF/py_robotiq_gripper/tree/master
# https://sdurobotics.gitlab.io/ur_rtde/examples/examples.html

import rtde_control  # > pip install ur-rtde  ggf. pip iupdaten mit > python.exe -m pip install --upgrade pip
import rtde_receive
# import rtde_io
import robotiq_gripper
# import time

import sys
from PyQt6 import QtWidgets, QtCore # ggf. pip install PyQt6
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtCore import QSize   
from PyQt6.QtWidgets import QPushButton 
from PyQt6.QtWidgets import QLabel

ROBOT_IP = "192.168.0.3"

class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)
        self.rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)
        self.gripper = robotiq_gripper.RobotiqGripper()
        self.gripper.connect(ROBOT_IP, 63352)

        self.setMinimumSize(QSize(400, 400))    
        self.setWindowTitle("SRO - Universal Robot GUI")

        self.btn_go_zp = QPushButton(' go +z up 5mm', self)
        self.btn_go_zp.clicked.connect(self.goSlot_zp)
        self.btn_go_zp.resize(100,30)
        self.btn_go_zp.move(150, 5)    

        self.btn_go_zm = QPushButton(' go -z down 5mm', self)
        self.btn_go_zm.clicked.connect(self.goSlot_zm)
        self.btn_go_zm.resize(100,30)
        self.btn_go_zm.move(150, 30)      

        self.btn_go_xp = QPushButton(' go +x 5mm', self)
        self.btn_go_xp.clicked.connect(self.goSlot_xp)
        self.btn_go_xp.resize(100,30)
        self.btn_go_xp.move(50, 5)    

        self.btn_go_xm = QPushButton(' go -x 5mm', self)
        self.btn_go_xm.clicked.connect(self.goSlot_xm)
        self.btn_go_xm.resize(100,30)
        self.btn_go_xm.move(50, 30)      

        self.btn_go_yp = QPushButton(' go +y 5mm', self)
        self.btn_go_yp.clicked.connect(self.goSlot_yp)
        self.btn_go_yp.resize(100,30)
        self.btn_go_yp.move(250, 5)    

        self.btn_go_ym = QPushButton(' go -y 5mm', self)
        self.btn_go_ym.clicked.connect(self.goSlot_ym)
        self.btn_go_ym.resize(100,30)
        self.btn_go_ym.move(250, 30)      


        self.btn_grp_open = QPushButton('open Gripper', self)
        self.btn_grp_open.clicked.connect(self.grpOpenSlot)
        self.btn_grp_open.resize(100, 30)
        self.btn_grp_open.move(150, 210)    

        self.btn_grp_close = QPushButton('close Gripper', self)
        self.btn_grp_close.clicked.connect(self.grpCloseSlot)
        self.btn_grp_close.resize(100, 30)
        self.btn_grp_close.move(150, 240)    

        self.pybutton = QPushButton(' update TCP Pose ', self)
        self.pybutton.clicked.connect(self.getTcpPoseSlot)
        self.pybutton.resize(100,30)
        self.pybutton.move(10, 60)     

        self.btn_teachOn = QPushButton(' Teach Mode ON ', self)
        self.btn_teachOn.clicked.connect(self.teachOnSlot)
        self.btn_teachOn.resize(100,30)
        self.btn_teachOn.move(10, 240)   
        self.btn_teachOn.setStyleSheet("background-color : yellow") 

        self.btn_teachOff = QPushButton(' Teach Mode OFF ', self)
        self.btn_teachOff.clicked.connect(self.teachOffSlot)
        self.btn_teachOff.resize(100,30)
        self.btn_teachOff.move(10, 260)
        self.btn_teachOff.setEnabled(False)     

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
        
        self.lbl_pose_complete = QLabel(" Pose Complete X Y Z  Y P R in m bzw. rad", self) 
        self.lbl_pose_complete.resize(500, 20)
        self.lbl_pose_complete.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.lbl_pose_complete.move(5, 300)

    def __del__(self):  # Destruktor
        print("Destruktor ")
        self.rtde_c.stopScript()
    
    def closeEvent(self, event):
        print("Close Event ")
        self.rtde_c.stopScript()

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
        self.lbl_pose_complete.setText(  str(round(self.pose[0], 3)) + ' ' 
                                       + str(round(self.pose[1], 3)) + ' ' 
                                       + str(round(self.pose[2], 3)) + '  '  
                                       + str(round(self.pose[3], 3)) + ' ' 
                                       + str(round(self.pose[4], 3)) + ' ' 
                                       + str(round(self.pose[5], 3)) + ' ' )

        self.log_info()
        grpr_pos = self.gripper.get_current_position()
        # self.lbl_gripper.setText('Gripper: ' + str(grpr_pos))
        if grpr_pos < 10:
            self.lbl_gripper.setText('Gripper is open: ' + str(grpr_pos))
        else:
            self.lbl_gripper.setText('Gripper is closed: ' + str(grpr_pos))
        
    def goSlot_zm(self):
        print('Move Robot down -z 0.005m')
        # get actual pose
        self.pose = self.rtde_r.getActualTCPPose() 
        # Inverse Kinematic im Roboter
        self.rtde_c.moveL([self.pose[0], 
                           self.pose[1],
                           self.pose[2] - 0.005,
                           self.pose[3],
                           self.pose[4], 
                           self.pose[5]], 0.3, 0.1)
        # update screen 
        self.getTcpPoseSlot()
    
    def goSlot_zp(self):
        print('Move Robot up +z 0.005m')
        # get actual pose
        self.pose = self.rtde_r.getActualTCPPose() 
        # Inverse Kinematic im Roboter
        self.rtde_c.moveL([self.pose[0],
                           self.pose[1],
                           self.pose[2]+ 0.005 ,
                           self.pose[3], 
                           self.pose[4], 
                           self.pose[5]], 0.3, 0.1)
        # update screen 
        self.getTcpPoseSlot()

    def goSlot_xp(self):
        print('Move Robot +x 0.005m')
        # get actual pose
        self.pose = self.rtde_r.getActualTCPPose() 
        # Inverse Kinematic im Roboter
        self.rtde_c.moveL([self.pose[0]+ 0.005,
                           self.pose[1],
                           self.pose[2],
                           self.pose[3], 
                           self.pose[4], 
                           self.pose[5]], 0.3, 0.1)
        # update screen 
        self.getTcpPoseSlot()  

    def goSlot_xm(self):
        print('Move Robot -x 0.005m')
        # get actual pose
        self.pose = self.rtde_r.getActualTCPPose() 
        # Inverse Kinematic im Roboter
        self.rtde_c.moveL([self.pose[0]- 0.005,
                           self.pose[1],
                           self.pose[2],
                           self.pose[3], 
                           self.pose[4], 
                           self.pose[5]], 0.3, 0.1)
        # update screen 
        self.getTcpPoseSlot()  
          
    def goSlot_yp(self):
        print('Move Robot +y 0.005m')
        # get actual pose
        self.pose = self.rtde_r.getActualTCPPose() 
        # Inverse Kinematic im Roboter
        self.rtde_c.moveL([self.pose[0],
                           self.pose[1]+ 0.005,
                           self.pose[2],
                           self.pose[3], 
                           self.pose[4], 
                           self.pose[5]], 0.3, 0.1)
        # update screen 
        self.getTcpPoseSlot()  

    def goSlot_ym(self):
        print('Move Robot -y 0.005m')
        # get actual pose
        self.pose = self.rtde_r.getActualTCPPose() 
        # Inverse Kinematic im Roboter
        self.rtde_c.moveL([self.pose[0],
                           self.pose[1]- 0.005,
                           self.pose[2],
                           self.pose[3], 
                           self.pose[4], 
                           self.pose[5]], 0.3, 0.1)
        # update screen 
        self.getTcpPoseSlot()  

    def grpInfo(self):
        grp_position = self.gripper.get_current_position()
        print("Actual Gripper Position is ")
        print (grp_position)    

    def grpOpenSlot(self):
        print('Open Gripper')
        self.grpInfo()
        # öffnet den Greifer
        grp_pos = self.gripper.get_current_position()
        self.gripper.move_and_wait_for_pos(grp_pos-10, 255, 255)
        

    def grpCloseSlot(self):
        print('Close Gripper')
        self.grpInfo()
        grp_pos = self.gripper.get_current_position()
        self.gripper.move_and_wait_for_pos(grp_pos+10, 255, 255)

    def teachOnSlot(self):
        print('Teachmode ON')
        self.rtde_c.teachMode()
        # changing color of button 
        self.btn_teachOn.setStyleSheet("background-color : red") 
        self.btn_teachOff.setEnabled(True) 
  

    def teachOffSlot(self):
        print('Teachmode OFF')
        self.rtde_c.endTeachMode()
        self.btn_teachOn.setStyleSheet("background-color : light gray") 
        self.btn_teachOff.setEnabled(False) 
       
       
   

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit( app.exec() )
