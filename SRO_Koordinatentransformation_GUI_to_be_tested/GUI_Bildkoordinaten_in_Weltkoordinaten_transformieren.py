#!/usr/bin/env python3
"""
TO BE TESTED - FILE under HEAVY DEVELOPMENT

PyQt6 GUI zur Transformation von Kamera-Koordinaten -> Roboter-Koordinaten
und zum Testen der Transformation mit einem UR-Roboter via ur_rtde.

Voraussetzungen:
    pip install pyqt6 ur_rtde numpy


Wie Sie das GUI praktisch nutzen

Kamera-zu-Basis-Transformation eintragen

Tx, Ty, Tz in Meter

Roll/Pitch/Yaw in Grad (z. B. Ergebnis Ihrer Hand-Eye-Kalibrierung)

Testpunkt aus RealSense eintragen

x_cam, y_cam, z_cam in Metern im Kamerakoordinatensystem
(z. B. Mittelpunkt eines erkannten Objekts)

Auf „Transformieren“ klicken
→ Sie sehen x_base, y_base, z_base und die 4×4-Matrix.

Wenn Sie einen UR angeschlossen haben:

IP setzen

„Verbinden“

„UR zu Punkt fahren (moveL)“ → Roboter fährt mit aktueller TCP-Orientierung über den berechneten Punkt.
"""

import sys
import math
import numpy as np

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QGroupBox, QPushButton, QLineEdit, QLabel,
    QDoubleSpinBox, QTextEdit
)
from PyQt6.QtCore import Qt

# ur_rtde optional importieren, damit das GUI auch ohne Roboter startet
try:
    from rtde_control import RTDEControlInterface
    from rtde_receive import RTDEReceiveInterface
except ImportError:
    RTDEControlInterface = None
    RTDEReceiveInterface = None


def rpy_to_rot_matrix(roll, pitch, yaw):
    """
    Roll, Pitch, Yaw (Rad) -> 3x3 Rotationsmatrix
    Konvention: R = Rz(yaw) * Ry(pitch) * Rx(roll)
    """
    cr = math.cos(roll)
    sr = math.sin(roll)
    cp = math.cos(pitch)
    sp = math.sin(pitch)
    cy = math.cos(yaw)
    sy = math.sin(yaw)

    Rz = np.array([[cy, -sy, 0],
                   [sy,  cy, 0],
                   [0,   0,  1]])

    Ry = np.array([[cp,  0, sp],
                   [0,   1, 0],
                   [-sp, 0, cp]])

    Rx = np.array([[1, 0,  0],
                   [0, cr, -sr],
                   [0, sr,  cr]])

    R = Rz @ Ry @ Rx
    return R


class CameraToRobotGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kamera → Roboter Transformation (UR + RTDE)")
        self.rtde_c = None
        self.rtde_r = None

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # ----- Roboter-Verbindung -----
        robot_group = QGroupBox("UR-Roboter Verbindung")
        robot_layout = QHBoxLayout(robot_group)
        self.ip_edit = QLineEdit("192.168.0.10")
        self.ip_edit.setPlaceholderText("UR IP-Adresse")
        self.connect_btn = QPushButton("Verbinden")
        self.disconnect_btn = QPushButton("Trennen")
        self.disconnect_btn.setEnabled(False)
        self.robot_status = QLabel("Status: nicht verbunden")

        self.connect_btn.clicked.connect(self.connect_robot)
        self.disconnect_btn.clicked.connect(self.disconnect_robot)

        robot_layout.addWidget(QLabel("IP:"))
        robot_layout.addWidget(self.ip_edit)
        robot_layout.addWidget(self.connect_btn)
        robot_layout.addWidget(self.disconnect_btn)
        robot_layout.addWidget(self.robot_status)

        # ----- Transformations-Parameter (T_base_cam) -----
        tf_group = QGroupBox("Transformation Kamera → Roboterbasis (T_base_cam)")
        tf_form = QFormLayout(tf_group)

        self.tx_spin = QDoubleSpinBox()
        self.ty_spin = QDoubleSpinBox()
        self.tz_spin = QDoubleSpinBox()
        for s in (self.tx_spin, self.ty_spin, self.tz_spin):
            s.setRange(-5.0, 5.0)
            s.setDecimals(4)
            s.setSingleStep(0.01)
        self.tx_spin.setValue(0.5)   # Beispielwerte
        self.ty_spin.setValue(0.0)
        self.tz_spin.setValue(0.4)

        self.roll_spin = QDoubleSpinBox()
        self.pitch_spin = QDoubleSpinBox()
        self.yaw_spin = QDoubleSpinBox()
        for s in (self.roll_spin, self.pitch_spin, self.yaw_spin):
            s.setRange(-180.0, 180.0)
            s.setDecimals(2)
            s.setSingleStep(1.0)
        # Beispiel: Kamera schaut von oben nach unten auf den Tisch
        self.roll_spin.setValue(180.0)
        self.pitch_spin.setValue(0.0)
        self.yaw_spin.setValue(0.0)

        tf_form.addRow("Tx [m]", self.tx_spin)
        tf_form.addRow("Ty [m]", self.ty_spin)
        tf_form.addRow("Tz [m]", self.tz_spin)
        tf_form.addRow("Roll [°]", self.roll_spin)
        tf_form.addRow("Pitch [°]", self.pitch_spin)
        tf_form.addRow("Yaw [°]", self.yaw_spin)

        # Anzeigen der aktuellen 4x4 Transformationsmatrix
        self.matrix_label = QTextEdit()
        self.matrix_label.setReadOnly(True)
        self.matrix_label.setFixedHeight(90)
        tf_form.addRow(QLabel("Homogene Matrix T_base_cam:"), self.matrix_label)

        # ----- Kamera-Punkt -----
        cam_group = QGroupBox("Punkt im Kamerakoordinatensystem (p_cam)")
        cam_form = QFormLayout(cam_group)

        self.cam_x = QDoubleSpinBox()
        self.cam_y = QDoubleSpinBox()
        self.cam_z = QDoubleSpinBox()
        for s in (self.cam_x, self.cam_y, self.cam_z):
            s.setRange(-5.0, 5.0)
            s.setDecimals(4)
            s.setSingleStep(0.005)

        self.cam_x.setValue(0.0)
        self.cam_y.setValue(0.0)
        self.cam_z.setValue(0.5)  # z.B. 0.5 m vor der Kamera

        cam_form.addRow("x_cam [m]", self.cam_x)
        cam_form.addRow("y_cam [m]", self.cam_y)
        cam_form.addRow("z_cam [m]", self.cam_z)

        # ----- Ergebnis: Punkt im Roboter-Basisframe -----
        base_group = QGroupBox("Transformierter Punkt im Roboter-Basisframe (p_base)")
        base_form = QFormLayout(base_group)

        self.base_x = QLineEdit()
        self.base_y = QLineEdit()
        self.base_z = QLineEdit()
        for e in (self.base_x, self.base_y, self.base_z):
            e.setReadOnly(True)

        base_form.addRow("x_base [m]", self.base_x)
        base_form.addRow("y_base [m]", self.base_y)
        base_form.addRow("z_base [m]", self.base_z)

        # Buttons
        btn_layout = QHBoxLayout()
        self.transform_btn = QPushButton("Transformieren")
        self.move_btn = QPushButton("UR zu Punkt fahren (moveL)")
        self.move_btn.setEnabled(False)

        self.transform_btn.clicked.connect(self.on_transform)
        self.move_btn.clicked.connect(self.on_move_robot)

        btn_layout.addWidget(self.transform_btn)
        btn_layout.addWidget(self.move_btn)

        # ----- Logfenster -----
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(120)

        # Alles in main_layout einhängen
        main_layout.addWidget(robot_group)
        main_layout.addWidget(tf_group)
        main_layout.addWidget(cam_group)
        main_layout.addWidget(base_group)
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(QLabel("Log:"))
        main_layout.addWidget(self.log_edit)

        self.update_matrix_label()

        # Änderungen an der TF sofort in Matrixansicht aktualisieren
        for s in (self.tx_spin, self.ty_spin, self.tz_spin,
                  self.roll_spin, self.pitch_spin, self.yaw_spin):
            s.valueChanged.connect(self.update_matrix_label)

    # ------------------------------------------------------------------
    # Robot Connection
    # ------------------------------------------------------------------
    def connect_robot(self):
        if RTDEControlInterface is None:
            self.log("ur_rtde ist nicht installiert. Nur Offline-Betrieb möglich.")
            return

        ip = self.ip_edit.text().strip()
        if not ip:
            self.log("Bitte eine IP-Adresse eingeben.")
            return

        try:
            self.rtde_c = RTDEControlInterface(ip)
            self.rtde_r = RTDEReceiveInterface(ip)
            self.robot_status.setText(f"Status: verbunden mit {ip}")
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.move_btn.setEnabled(True)
            self.log(f"Erfolgreich mit UR-Roboter {ip} verbunden.")
        except Exception as e:
            self.rtde_c = None
            self.rtde_r = None
            self.robot_status.setText("Status: Verbindung fehlgeschlagen")
            self.log(f"Fehler bei Verbindung: {e}")

    def disconnect_robot(self):
        if self.rtde_c is not None:
            try:
                self.rtde_c.stopScript()
            except Exception:
                pass
        self.rtde_c = None
        self.rtde_r = None
        self.robot_status.setText("Status: nicht verbunden")
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.move_btn.setEnabled(False)
        self.log("Verbindung zum Roboter getrennt.")

    # ------------------------------------------------------------------
    # Transformation Camera -> Robot
    # ------------------------------------------------------------------
    def get_transform_matrix(self):
        """
        Liest Tx,Ty,Tz und Roll/Pitch/Yaw aus den Spinboxen
        und liefert die homogene 4x4 Transformationsmatrix T_base_cam.
        """
        tx = self.tx_spin.value()
        ty = self.ty_spin.value()
        tz = self.tz_spin.value()

        roll_deg = self.roll_spin.value()
        pitch_deg = self.pitch_spin.value()
        yaw_deg = self.yaw_spin.value()

        roll = math.radians(roll_deg)
        pitch = math.radians(pitch_deg)
        yaw = math.radians(yaw_deg)

        R = rpy_to_rot_matrix(roll, pitch, yaw)
        t = np.array([[tx], [ty], [tz]])

        T = np.eye(4)
        T[0:3, 0:3] = R
        T[0:3, 3:4] = t
        return T

    def update_matrix_label(self):
        T = self.get_transform_matrix()
        text_lines = []
        for row in range(4):
            text_lines.append(
                " ".join(f"{T[row, col]: .4f}" for col in range(4))
            )
        self.matrix_label.setPlainText("\n".join(text_lines))

    def on_transform(self):
        """
        Button-Handler: Punkt im Kameraframe in Roboterbasis transformieren.
        """
        T = self.get_transform_matrix()
        p_cam = np.array([[self.cam_x.value()],
                          [self.cam_y.value()],
                          [self.cam_z.value()],
                          [1.0]])

        p_base = T @ p_cam
        x_b = float(p_base[0, 0])
        y_b = float(p_base[1, 0])
        z_b = float(p_base[2, 0])

        self.base_x.setText(f"{x_b:.4f}")
        self.base_y.setText(f"{y_b:.4f}")
        self.base_z.setText(f"{z_b:.4f}")

        self.log(f"Transformiert: p_cam = ({self.cam_x.value():.4f}, "
                 f"{self.cam_y.value():.4f}, {self.cam_z.value():.4f}) "
                 f"→ p_base = ({x_b:.4f}, {y_b:.4f}, {z_b:.4f})")

    # ------------------------------------------------------------------
    # Bewegung des UR zum transformierten Punkt
    # ------------------------------------------------------------------
    def on_move_robot(self):
        if self.rtde_c is None or self.rtde_r is None:
            self.log("Nicht mit Roboter verbunden.")
            return

        try:
            x_b = float(self.base_x.text())
            y_b = float(self.base_y.text())
            z_b = float(self.base_z.text())
        except ValueError:
            self.log("Bitte zuerst transformieren (gültige p_base-Werte).")
            return

        try:
            current_pose = self.rtde_r.getActualTCPPose()  # [x,y,z,rx,ry,rz]
            new_pose = list(current_pose)
            new_pose[0] = x_b
            new_pose[1] = y_b
            new_pose[2] = z_b + 0.05  # z.B. 5 cm über Objekt

            self.log(f"Fahre mit moveL zu: {new_pose}")
            self.rtde_c.moveL(new_pose, 0.1, 0.2)
            self.log("Bewegung abgeschlossen.")
        except Exception as e:
            self.log(f"Fehler bei moveL: {e}")

    # ------------------------------------------------------------------
    def log(self, msg: str):
        self.log_edit.append(msg)
        self.log_edit.moveCursor(self.log_edit.textCursor().MoveOperation.End)


def main():
    app = QApplication(sys.argv)
    win = CameraToRobotGUI()
    win.resize(900, 700)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
