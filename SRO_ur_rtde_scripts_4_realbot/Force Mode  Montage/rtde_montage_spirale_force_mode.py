"""
THIS FILE IS UNDER HEAVY CONSTRUCTION

ur_rtde Skript für die Montage eines Objekts per Spiralbewegung unter konstantem Kraftstoß nach unten. 
Im GUI gibst du Zielpose, Kraft und Spiral-Parameter ein; der Roboter fährt die Spirale im Kraftmodus ab. 
Das Skript orientiert sich an der Dokumentation und Praxis für UR-e-Roboter mit Force-Mode."""

import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout
)
import numpy as np
import time

import rtde_control
import rtde_receive

ROBOT_IP = "192.168.0.3"  # setze IP passend

def generate_spiral_points(center_pose, radius, steps, revolutions, height_step):
    points = []
    for i in range(steps * revolutions):
        theta = 2 * np.pi * i / steps
        r = radius * (i / (steps * revolutions))
        x = center_pose[0] + r * np.cos(theta)
        y = center_pose[1] + r * np.sin(theta)
        z = center_pose[2] + height_step * (i / (steps * revolutions))
        pose = [x, y, z, center_pose[3], center_pose[4], center_pose[5]]
        points.append(pose)
    return points

class SpiralForceGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spiralförmige Montage mit Kraft (PyQt6)")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        hlayout = QHBoxLayout()
        self.pose_edits = [QLineEdit(str(val)) for val in [0.3, 0.0, 0.1, 0.0, 3.14, 0.0]]
        for i, label in enumerate(["X", "Y", "Z", "RX", "RY", "RZ"]):
            hlayout.addWidget(QLabel(label))
            hlayout.addWidget(self.pose_edits[i])

        layout.addLayout(hlayout)

        self.force_edit = QLineEdit("30")
        layout.addWidget(QLabel("Kraft nach unten [N]"))
        layout.addWidget(self.force_edit)

        self.radius_edit = QLineEdit("0.01")
        self.steps_edit = QLineEdit("36")
        self.rev_edit = QLineEdit("3")
        self.hstep_edit = QLineEdit("0.0")
        layout.addWidget(QLabel("Spiralradius [m]"))
        layout.addWidget(self.radius_edit)
        layout.addWidget(QLabel("Schritte/Umdrehung"))
        layout.addWidget(self.steps_edit)
        layout.addWidget(QLabel("Anzahl Umdrehungen"))
        layout.addWidget(self.rev_edit)
        layout.addWidget(QLabel("Z-Schritt pro Umdrehung [m]"))
        layout.addWidget(self.hstep_edit)

        self.btn_start = QPushButton("Montage starten")
        self.btn_start.clicked.connect(self.start_montage)
        layout.addWidget(self.btn_start)

        self.setLayout(layout)

    def start_montage(self):
        pose = [float(e.text()) for e in self.pose_edits]
        force = float(self.force_edit.text())
        radius = float(self.radius_edit.text())
        steps = int(self.steps_edit.text())
        revs = int(self.rev_edit.text())
        hstep = float(self.hstep_edit.text())

        points = generate_spiral_points(pose, radius, steps, revs, hstep)
        rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)

        task_frame = pose
        selection_vector = [0, 0, 1, 0, 0, 0]
        wrench = [0, 0, -force, 0, 0, 0]
        force_type = 2
        limits = [10, 10, 5, 1, 1, 1]

        rtde_c.forceModeStart(task_frame, selection_vector, wrench, force_type, limits)
        for p in points:
            rtde_c.moveL(p, 0.05, 0.1)
            time.sleep(0.1)
        rtde_c.forceModeStop()
        rtde_c.stopScript()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SpiralForceGUI()
    win.show()
    sys.exit(app.exec())
