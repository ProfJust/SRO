# usage. C:/Python312/python.exe c:/mySciebo/_EMR25/github/emr25/controllers/rtde-Simulation/Webots_GUI_controller.py


import sys
import json
import socket
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer
import math as m

class RobotControlGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.current_angles = [0.0] * 6
        self.initUI()
        self.connect_to_robot()

    def initUI(self):
        self.setWindowTitle('W-HS - Embedded Robotics - UR3e Joint Control')
        layout = QVBoxLayout()

        self.joint_sliders = []
        self.value_labels = []
        joint_ranges = [
            (-3.14, 3.14),
            (-3.14159, 3.14159),
            (-6.14159, 6.14159),
            (-3.14, 3.14),
            (-3.14, 3.14),
            (-3.14, 3.14)
        ]

        for i, (min_val, max_val) in enumerate(joint_ranges):
            group = QGroupBox(f'Gelenk {i+1} ({["Basis", "Schulter", "Ellbogen", "Wrist 1", "Wrist 2", "Wrist 3"][i]})')
            vbox = QVBoxLayout()

            lbl = QLabel('0.00 rad')
            self.value_labels.append(lbl)

            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(int(min_val * 100))
            slider.setMaximum(int(max_val * 100))
            slider.valueChanged.connect(lambda value, idx=i: self.slider_changed(value, idx))

            vbox.addWidget(lbl)
            vbox.addWidget(slider)
            group.setLayout(vbox)
            self.joint_sliders.append(slider)
            layout.addWidget(group)

        self.status_label = QLabel("Verbindung wird hergestellt...")
        layout.addWidget(self.status_label)

        gripper_buttons = QHBoxLayout()
        self.btn_open = QPushButton("Greifer öffnen")
        self.btn_close = QPushButton("Greifer schließen")
        self.btn_open.clicked.connect(self.open_gripper)
        self.btn_close.clicked.connect(self.close_gripper)
        gripper_buttons.addWidget(self.btn_open)
        gripper_buttons.addWidget(self.btn_close)
        layout.addLayout(gripper_buttons)

        # Geschwindigkeitsregler für UR
        speed_layout = QVBoxLayout()

        self.ur_speed_slider = QSlider(Qt.Horizontal)
        self.ur_speed_slider.setMinimum(10)
        self.ur_speed_slider.setMaximum(100)
        self.ur_speed_slider.setValue(50)
        self.ur_speed_slider.setTickPosition(QSlider.TicksBelow)
        self.ur_speed_slider.setTickInterval(10)

        self.ur_speed_label = QLabel("UR Geschwindigkeit: 0.50")
        self.ur_speed_slider.valueChanged.connect(
            lambda val: self.ur_speed_label.setText(f"UR Geschwindigkeit: {val / 100:.2f}")
        )

        speed_layout.addWidget(self.ur_speed_label)
        speed_layout.addWidget(self.ur_speed_slider)
        layout.addLayout(speed_layout)

        self.setLayout(layout)
        self.setMinimumSize(1000, 700)

    def connect_to_robot(self):
        try:
            self.sock.connect(('localhost', 30010))
            self.status_label.setText("Verbunden mit Roboter")
            self.status_label.setStyleSheet("color: green")

            self.request_current_angles()
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self.request_current_angles)
            self.update_timer.start(500)
        except socket.error as e:
            self.status_label.setText(f"Verbindungsfehler: {str(e)}")
            self.status_label.setStyleSheet("color: red")

    def open_gripper(self):
        try:
            self.sock.sendall(json.dumps({"command": "openGripper"}).encode('utf-8'))
            response = self.sock.recv(4096)
            print("🟢 Greifer öffnen gesendet. Antwort:", response.decode())
        except Exception as e:
            print("⚠️ Fehler beim Öffnen des Greifers:", e)

    def close_gripper(self):
        try:
            self.sock.sendall(json.dumps({"command": "closeGripper"}).encode('utf-8'))
            response = self.sock.recv(4096)
            print("🔴 Greifer schließen gesendet. Antwort:", response.decode())
        except Exception as e:
            print("⚠️ Fehler beim Schließen des Greifers:", e)

    def request_current_angles(self):
        try:
            cmd = json.dumps({"command": "getActualQ"})
            self.sock.sendall(cmd.encode('utf-8'))
            response = self.sock.recv(4096)
            data = json.loads(response.decode())
            if 'data' in data:
                self.current_angles = data['data']
                self.update_sliders()
        except Exception as e:
            print("Abfragefehler:", str(e))

    def update_sliders(self):
        for slider in self.joint_sliders:
            slider.blockSignals(True)
        for i, angle in enumerate(self.current_angles):
            self.joint_sliders[i].setValue(int(angle * 100))
            self.value_labels[i].setText(f"{angle:.2f} rad   {angle/m.pi*180.0:.2f} deg")
            # print(f" real (x, y, z): {T.t[0]:.2f}, {T.t[2]:.2f}, {T.t[1]:.2f}")
        for slider in self.joint_sliders:
            slider.blockSignals(False)

    def slider_changed(self, value, joint_index):
        rad_value = value / 100.0
        self.current_angles[joint_index] = rad_value
        self.send_joint_command()

    def send_joint_command(self):
        speed_val = self.ur_speed_slider.value() / 100.0
        command = {
            "command": "moveJ",
            "data": self.current_angles.copy(),
            "speed": speed_val
        }
        try:
            self.sock.sendall(json.dumps(command).encode('utf-8'))
            response = self.sock.recv(4096)
            print("Serverantwort:", response.decode())
        except Exception as e:
            print("Kommunikationsfehler:", str(e))

    def closeEvent(self, event):
        self.sock.close()
        self.update_timer.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = RobotControlGUI()
    ex.show()
    sys.exit(app.exec_())
