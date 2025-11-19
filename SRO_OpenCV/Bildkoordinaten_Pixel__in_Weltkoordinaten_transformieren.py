#!/usr/bin/env python3
"""
PyQt6 GUI zur Transformation von Bildkoordinaten (Pixel + Tiefe)
über Kamerakoordinaten -> Roboter-Koordinaten (UR + RTDE).

Voraussetzungen:
    pip install pyqt6 ur_rtde numpy


Hinweis zur Praxis:

fx, fy, cx, cy holen Sie idealerweise aus der camera_info-Message der RealSense (/camera/color/camera_info) oder aus dem RealSense Viewer.

Die Tiefe Z kommt aus der Depth-Map (in Meter umgerechnet).

Damit können Sie im Labor wunderbar testen, ob Ihre Hand-Eye-Kalibrierung passt:
Pixel anklicken → Werte eintragen → Roboter zum Punkt fahren lassen → sollte über dem Objekt stehen.

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
        self.setWindowTitle("Pixel → Kamera → Roboter Transformation (UR + RTDE)")
        self.rtde_c = None
        self.rtde_r = None

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # ===== Roboter-Verbindung =====
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

        # ===== Transformation Kamera → Roboterbasis (extrinsisch) =====
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
        self.roll_spin.setValue(180.0)
        self.pitch_spin.setValue(0.0)
        self.yaw_spin.setValue(0.0)

        tf_form.addRow("Tx [m]", self.tx_spin)
        tf_form.addRow("Ty [m]", self.ty_spin)
        tf_form.addRow("Tz [m]", self.tz_spin)
        tf_form.addRow("Roll [°]", self.roll_spin)
        tf_form.addRow("Pitch [°]", self.pitch_spin)
        tf_form.addRow("Yaw [°]", self.yaw_spin)

        self.matrix_label = QTextEdit()
        self.matrix_label.setReadOnly(True)
        self.matrix_label.setFixedHeight(90)
        tf_form.addRow(QLabel("Homogene Matrix T_base_cam:"), self.matrix_label)

        # ===== Kameraintrinsik (fx, fy, cx, cy) =====
        intr_group = QGroupBox("Kameraintrinsische Parameter (z.B. RealSense color)")
        intr_form = QFormLayout(intr_group)

        self.fx_spin = QDoubleSpinBox()
        self.fy_spin = QDoubleSpinBox()
        self.cx_spin = QDoubleSpinBox()
        self.cy_spin = QDoubleSpinBox()
        for s in (self.fx_spin, self.fy_spin):
            s.setRange(100.0, 5000.0)
            s.setDecimals(2)
            s.setSingleStep(10.0)
        for s in (self.cx_spin, self.cy_spin):
            s.setRange(0.0, 4000.0)
            s.setDecimals(2)
            s.setSingleStep(1.0)

        # Beispielwerte für eine 1280x720-Kamera (müssen Sie aus camera_info übernehmen)
        self.fx_spin.setValue(900.0)
        self.fy_spin.setValue(900.0)
        self.cx_spin.setValue(640.0)
        self.cy_spin.setValue(360.0)

        intr_form.addRow("fx [Pixel]", self.fx_spin)
        intr_form.addRow("fy [Pixel]", self.fy_spin)
        intr_form.addRow("cx [Pixel]", self.cx_spin)
        intr_form.addRow("cy [Pixel]", self.cy_spin)

        # ===== Bildkoordinaten (Pixel + Tiefe) =====
        cam_group = QGroupBox("Bildkoordinaten + Tiefe")
        cam_form = QFormLayout(cam_group)

        self.u_pix = QDoubleSpinBox()
        self.v_pix = QDoubleSpinBox()
        self.depth_z = QDoubleSpinBox()
        for s in (self.u_pix, self.v_pix):
            s.setRange(0.0, 4000.0)
            s.setDecimals(2)
            s.setSingleStep(1.0)
        self.depth_z.setRange(0.0, 5.0)
        self.depth_z.setDecimals(4)
        self.depth_z.setSingleStep(0.01)

        self.u_pix.setValue(640.0)
        self.v_pix.setValue(360.0)
        self.depth_z.setValue(0.5)  # 0.5 m vor der Kamera

        cam_form.addRow("u [Pixel]", self.u_pix)
        cam_form.addRow("v [Pixel]", self.v_pix)
        cam_form.addRow("Tiefe Z [m]", self.depth_z)

        # ===== 3D-Punkt im Kameraframe (zur Kontrolle) =====
        cam3d_group = QGroupBox("Berechneter Punkt im Kameraframe (p_cam)")
        cam3d_form = QFormLayout(cam3d_group)

        self.cam_x = QLineEdit()
        self.cam_y = QLineEdit()
        self.cam_z = QLineEdit()
        for e in (self.cam_x, self.cam_y, self.cam_z):
            e.setReadOnly(True)

        cam3d_form.addRow("x_cam [m]", self.cam_x)
        cam3d_form.addRow("y_cam [m]", self.cam_y)
        cam3d_form.addRow("z_cam [m]", self.cam_z)

        # ===== Ergebnis im Roboterbasis-Frame =====
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

        # ===== Buttons =====
        btn_layout = QHBoxLayout()
        self.transform_btn = QPushButton("Transformieren (Pixel → Welt)")
        self.move_btn = QPushButton("UR zu Punkt fahren (moveL)")
        self.move_btn.setEnabled(False)

        self.transform_btn.clicked.connect(self.on_transform)
        self.move_btn.clicked.connect(self.on_move_robot)

        btn_layout.addWidget(self.transform_btn)
        btn_layout.addWidget(self.move_btn)

        # ===== Logfenster =====
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(120)

        # Alles ins Hauptlayout
        main_layout.addWidget(robot_group)
        main_layout.addWidget(tf_group)
        main_layout.addWidget(intr_group)
        main_layout.addWidget(cam_group)
        main_layout.addWidget(cam3d_group)
        main_layout.addWidget(base_group)
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(QLabel("Log:"))
        main_layout.addWidget(self.log_edit)

        self.update_matrix_label()

        for s in (self.tx_spin, self.ty_spin, self.tz_spin,
                  self.roll_spin, self.pitch_spin, self.yaw_spin):
            s.valueChanged.connect(self.update_matrix_label)

    # ===== Robot Connection =====
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

    # ===== Transformationen =====
    def get_transform_matrix(self):
        """Liest Tx,Ty,Tz und Roll/Pitch/Yaw aus und liefert T_base_cam."""
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
            text_lines.append(" ".join(f"{T[row, col]: .4f}" for col in range(4)))
        self.matrix_label.setPlainText("\n".join(text_lines))

    def pixel_to_camera(self, u, v, depth, fx, fy, cx, cy):
        """Projiziert Pixel (u,v) + Tiefe in 3D-Kamerakoordinaten."""
        if depth <= 0.0:
            raise ValueError("Tiefe muss > 0 sein.")
        X = (u - cx) * depth / fx
        Y = (v - cy) * depth / fy
        Z = depth
        return X, Y, Z

    def on_transform(self):
        """
        Button: Pixel → Kamerakoordinaten → Roboterbasis.
        """
        # 1) Pixel + Tiefe einlesen
        u = self.u_pix.value()
        v = self.v_pix.value()
        depth = self.depth_z.value()

        fx = self.fx_spin.value()
        fy = self.fy_spin.value()
        cx = self.cx_spin.value()
        cy = self.cy_spin.value()

        try:
            Xc, Yc, Zc = self.pixel_to_camera(u, v, depth, fx, fy, cx, cy)
        except Exception as e:
            self.log(f"Fehler Pixel→Kamera: {e}")
            return

        # 2) im GUI anzeigen
        self.cam_x.setText(f"{Xc:.4f}")
        self.cam_y.setText(f"{Yc:.4f}")
        self.cam_z.setText(f"{Zc:.4f}")

        # 3) Kamera → Roboterbasis transformieren
        T = self.get_transform_matrix()
        p_cam = np.array([[Xc], [Yc], [Zc], [1.0]])
        p_base = T @ p_cam
        x_b = float(p_base[0, 0])
        y_b = float(p_base[1, 0])
        z_b = float(p_base[2, 0])

        self.base_x.setText(f"{x_b:.4f}")
        self.base_y.setText(f"{y_b:.4f}")
        self.base_z.setText(f"{z_b:.4f}")

        self.log(
            f"Pixel (u={u:.1f}, v={v:.1f}, Z={depth:.3f} m) → "
            f"p_cam=({Xc:.4f}, {Yc:.4f}, {Zc:.4f}) → "
            f"p_base=({x_b:.4f}, {y_b:.4f}, {z_b:.4f})"
        )

    # ===== Bewegung des UR-Roboters =====
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

    def log(self, msg: str):
        self.log_edit.append(msg)
        self.log_edit.moveCursor(self.log_edit.textCursor().MoveOperation.End)


def main():
    app = QApplication(sys.argv)
    win = CameraToRobotGUI()
    win.resize(950, 800)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
