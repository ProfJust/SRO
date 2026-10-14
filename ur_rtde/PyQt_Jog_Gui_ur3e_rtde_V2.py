import sys
import math
import threading
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtWidgets import (
    QApplication, QWidget, QGridLayout, QPushButton, QLineEdit,
    QDoubleSpinBox, QLabel, QGroupBox, QHBoxLayout, QVBoxLayout
)

# ur_rtde
try:
    import rtde_control
    import rtde_receive
except ImportError:
    rtde_control = None
    rtde_receive = None


class URJogGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UR3e Jog GUI (ur_rtde · TCP Jog + Pose)")
        self.setMinimumWidth(640)

        # RTDE handles
        self.rtde_c = None
        self.rtde_r = None
        self.connected = False

        # Jog-Status
        self.current_twist = [0, 0, 0, 0, 0, 0]  # [vx,vy,vz,wx,wy,wz]  m/s, rad/s
        self.jog_active = False
        self.lock = threading.Lock()

        # UI
        self._build_ui()

        # Timer: sendet Jog & aktualisiert Pose
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(100)    # 100 ms
        self.timer.timeout.connect(self._tick)

    # ---------------- UI -----------------
    def _build_ui(self):
        main = QVBoxLayout(self)

        # Verbindung
        conn_box = QGroupBox("Verbindung")
        conn_layout = QGridLayout()
        self.ip_edit = QLineEdit("192.168.0.100")
        self.ip_edit.setPlaceholderText("Roboter IP-Adresse")
        self.connect_btn = QPushButton("Verbinden")
        self.disconnect_btn = QPushButton("Trennen")
        self.disconnect_btn.setEnabled(False)

        conn_layout.addWidget(QLabel("UR3e IP:"), 0, 0)
        conn_layout.addWidget(self.ip_edit, 0, 1)
        conn_layout.addWidget(self.connect_btn, 0, 2)
        conn_layout.addWidget(self.disconnect_btn, 0, 3)
        conn_box.setLayout(conn_layout)
        main.addWidget(conn_box)

        # Parameter
        param_box = QGroupBox("Jog-Parameter (TCP)")
        param_layout = QGridLayout()

        self.lin_speed_spin = QDoubleSpinBox()
        self.lin_speed_spin.setRange(0.0, 0.5)  # m/s
        self.lin_speed_spin.setDecimals(3)
        self.lin_speed_spin.setSingleStep(0.01)
        self.lin_speed_spin.setValue(0.050)

        self.ang_speed_spin = QDoubleSpinBox()
        self.ang_speed_spin.setRange(0.0, 2.0)  # rad/s
        self.ang_speed_spin.setDecimals(3)
        self.ang_speed_spin.setSingleStep(0.05)
        self.ang_speed_spin.setValue(0.20)

        self.acc_spin = QDoubleSpinBox()
        self.acc_spin.setRange(0.1, 5.0)   # m/s^2 (wir nutzen dieselbe acc für speedL)
        self.acc_spin.setDecimals(2)
        self.acc_spin.setSingleStep(0.1)
        self.acc_spin.setValue(0.5)

        param_layout.addWidget(QLabel("Linear v [m/s]:"), 0, 0)
        param_layout.addWidget(self.lin_speed_spin, 0, 1)
        param_layout.addWidget(QLabel("Angular ω [rad/s]:"), 0, 2)
        param_layout.addWidget(self.ang_speed_spin, 0, 3)
        param_layout.addWidget(QLabel("Beschl. [m/s²]:"), 1, 0)
        param_layout.addWidget(self.acc_spin, 1, 1)
        param_box.setLayout(param_layout)
        main.addWidget(param_box)

        # Jog Buttons Translation
        jog_lin_box = QGroupBox("Jog (Translation TCP)")
        grid_lin = QGridLayout()
        self.btn_xp = QPushButton("+X")
        self.btn_xm = QPushButton("−X")
        self.btn_yp = QPushButton("+Y")
        self.btn_ym = QPushButton("−Y")
        self.btn_zp = QPushButton("+Z")
        self.btn_zm = QPushButton("−Z")
        for b in [self.btn_xp, self.btn_xm, self.btn_yp, self.btn_ym, self.btn_zp, self.btn_zm]:
            b.setMinimumHeight(48)
        grid_lin.addWidget(self.btn_xp, 0, 0)
        grid_lin.addWidget(self.btn_yp, 0, 1)
        grid_lin.addWidget(self.btn_zp, 0, 2)
        grid_lin.addWidget(self.btn_xm, 1, 0)
        grid_lin.addWidget(self.btn_ym, 1, 1)
        grid_lin.addWidget(self.btn_zm, 1, 2)
        jog_lin_box.setLayout(grid_lin)
        main.addWidget(jog_lin_box)

        # Jog Buttons Rotation
        jog_rot_box = QGroupBox("Jog (Rotation TCP)")
        grid_rot = QGridLayout()
        self.btn_rxp = QPushButton("+Rx")
        self.btn_rxm = QPushButton("−Rx")
        self.btn_ryp = QPushButton("+Ry")
        self.btn_rym = QPushButton("−Ry")
        self.btn_rzp = QPushButton("+Rz")
        self.btn_rzm = QPushButton("−Rz")
        for b in [self.btn_rxp, self.btn_rxm, self.btn_ryp, self.btn_rym, self.btn_rzp, self.btn_rzm]:
            b.setMinimumHeight(48)
        grid_rot.addWidget(self.btn_rxp, 0, 0)
        grid_rot.addWidget(self.btn_ryp, 0, 1)
        grid_rot.addWidget(self.btn_rzp, 0, 2)
        grid_rot.addWidget(self.btn_rxm, 1, 0)
        grid_rot.addWidget(self.btn_rym, 1, 1)
        grid_rot.addWidget(self.btn_rzm, 1, 2)
        jog_rot_box.setLayout(grid_rot)
        main.addWidget(jog_rot_box)

        # Pose Anzeige
        pose_box = QGroupBox("Aktuelle TCP-Pose")
        pose_grid = QGridLayout()
        self.lbl_x = QLabel("--")
        self.lbl_y = QLabel("--")
        self.lbl_z = QLabel("--")
        self.lbl_rx = QLabel("--")
        self.lbl_ry = QLabel("--")
        self.lbl_rz = QLabel("--")
        pose_grid.addWidget(QLabel("X [mm]:"), 0, 0); pose_grid.addWidget(self.lbl_x, 0, 1)
        pose_grid.addWidget(QLabel("Y [mm]:"), 0, 2); pose_grid.addWidget(self.lbl_y, 0, 3)
        pose_grid.addWidget(QLabel("Z [mm]:"), 0, 4); pose_grid.addWidget(self.lbl_z, 0, 5)
        pose_grid.addWidget(QLabel("Rx [°]:"), 1, 0); pose_grid.addWidget(self.lbl_rx, 1, 1)
        pose_grid.addWidget(QLabel("Ry [°]:"), 1, 2); pose_grid.addWidget(self.lbl_ry, 1, 3)
        pose_grid.addWidget(QLabel("Rz [°]:"), 1, 4); pose_grid.addWidget(self.lbl_rz, 1, 5)
        pose_box.setLayout(pose_grid)
        main.addWidget(pose_box)

        # Status & Stopp
        bottom = QHBoxLayout()
        self.status_lbl = QLabel("Getrennt")
        self.estop_btn = QPushButton("Stopp (speedStop)")
        self.estop_btn.setStyleSheet("QPushButton { font-weight: bold; }")
        self.estop_btn.setEnabled(False)
        bottom.addWidget(self.status_lbl)
        bottom.addStretch(1)
        bottom.addWidget(self.estop_btn)
        main.addLayout(bottom)

        # Signals
        self.connect_btn.clicked.connect(self.connect_robot)
        self.disconnect_btn.clicked.connect(self.disconnect_robot)
        self.estop_btn.clicked.connect(self.estop)

        # Press-and-hold für Translation
        self._wire_hold_button(self.btn_xp, axis=0, sign=+1, rotational=False)
        self._wire_hold_button(self.btn_xm, axis=0, sign=-1, rotational=False)
        self._wire_hold_button(self.btn_yp, axis=1, sign=+1, rotational=False)
        self._wire_hold_button(self.btn_ym, axis=1, sign=-1, rotational=False)
        self._wire_hold_button(self.btn_zp, axis=2, sign=+1, rotational=False)
        self._wire_hold_button(self.btn_zm, axis=2, sign=-1, rotational=False)

        # Press-and-hold für Rotation
        self._wire_hold_button(self.btn_rxp, axis=3, sign=+1, rotational=True)
        self._wire_hold_button(self.btn_rxm, axis=3, sign=-1, rotational=True)
        self._wire_hold_button(self.btn_ryp, axis=4, sign=+1, rotational=True)
        self._wire_hold_button(self.btn_rym, axis=4, sign=-1, rotational=True)
        self._wire_hold_button(self.btn_rzp, axis=5, sign=+1, rotational=True)
        self._wire_hold_button(self.btn_rzm, axis=5, sign=-1, rotational=True)

        self._set_controls_enabled(False)

    def _wire_hold_button(self, btn: QPushButton, axis: int, sign: int, rotational: bool):
        btn.pressed.connect(lambda: self._start_jog(axis, sign, rotational))
        btn.released.connect(self._stop_jog)

    def _set_controls_enabled(self, enabled: bool):
        for b in [
            self.btn_xp, self.btn_xm, self.btn_yp, self.btn_ym, self.btn_zp, self.btn_zm,
            self.btn_rxp, self.btn_rxm, self.btn_ryp, self.btn_rym, self.btn_rzp, self.btn_rzm,
            self.estop_btn
        ]:
            b.setEnabled(enabled)

    # -------------- Verbindung --------------
    def connect_robot(self):
        if self.connected:
            return
        if rtde_control is None or rtde_receive is None:
            QtWidgets.QMessageBox.critical(self, "Fehler",
                                           "ur_rtde ist nicht installiert (pip install ur_rtde).")
            return
        ip = self.ip_edit.text().strip()
        try:
            self.rtde_c = rtde_control.RTDEControlInterface(ip)
            self.rtde_r = rtde_receive.RTDEReceiveInterface(ip)
            self.connected = True
            self.status_lbl.setText(f"Verbunden mit {ip}")
            self._set_controls_enabled(True)
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.timer.start()
        except Exception as e:
            self.rtde_c = None
            self.rtde_r = None
            self.connected = False
            self.status_lbl.setText("Verbindungsfehler")
            QtWidgets.QMessageBox.critical(self, "Verbindung fehlgeschlagen", str(e))

    def disconnect_robot(self):
        self.timer.stop()
        self._stop_jog()
        try:
            if self.rtde_c:
                try:
                    self.rtde_c.speedStop()
                except Exception:
                    pass
                self.rtde_c.disconnect()
            if self.rtde_r:
                self.rtde_r.disconnect()
        finally:
            self.rtde_c = None
            self.rtde_r = None
            self.connected = False
            self._set_controls_enabled(False)
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            self.status_lbl.setText("Getrennt")
            self._clear_pose_labels()

    # -------------- Jogging --------------
    def _start_jog(self, axis: int, sign: int, rotational: bool):
        if not self.connected or self.rtde_c is None:
            return
        v_lin = self.lin_speed_spin.value()
        v_ang = self.ang_speed_spin.value()
        twist = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        if rotational:
            twist[axis] = sign * v_ang  # rad/s in [3..5]
        else:
            twist[axis] = sign * v_lin  # m/s in [0..2]
        with self.lock:
            self.current_twist = twist
            self.jog_active = True

    def _stop_jog(self):
        with self.lock:
            self.jog_active = False
            self.current_twist = [0, 0, 0, 0, 0, 0]
        try:
            if self.rtde_c:
                self.rtde_c.speedStop()
        except Exception:
            pass

    def estop(self):
        self._stop_jog()

    # -------------- Timer --------------
    def _tick(self):
        """Alle 100 ms: ggf. speedL senden und Pose aktualisieren."""
        if not self.connected:
            return

        # 1) Jog Command
        try:
            with self.lock:
                jog = self.jog_active
                twist = list(self.current_twist)
            if jog and self.rtde_c:
                acc = self.acc_spin.value()
                self.rtde_c.speedL(twist, acc, 0.1)  # time=0.1s
        except Exception as e:
            self._stop_jog()
            self.status_lbl.setText(f"Fehler: {e}")

        # 2) Pose lesen & anzeigen
        try:
            if self.rtde_r:
                pose = self.rtde_r.getActualTCPPose()  # [x,y,z,rx,ry,rz]
                if pose and len(pose) == 6:
                    x_mm = pose[0] * 1000.0
                    y_mm = pose[1] * 1000.0
                    z_mm = pose[2] * 1000.0
                    rx_deg = math.degrees(pose[3])
                    ry_deg = math.degrees(pose[4])
                    rz_deg = math.degrees(pose[5])
                    self.lbl_x.setText(f"{x_mm: .2f}")
                    self.lbl_y.setText(f"{y_mm: .2f}")
                    self.lbl_z.setText(f"{z_mm: .2f}")
                    self.lbl_rx.setText(f"{rx_deg: .2f}")
                    self.lbl_ry.setText(f"{ry_deg: .2f}")
                    self.lbl_rz.setText(f"{rz_deg: .2f}")
        except Exception:
            # Pose-Fehler nicht zu laut, Anzeige einfach nicht aktualisieren
            pass

    def _clear_pose_labels(self):
        for w in [self.lbl_x, self.lbl_y, self.lbl_z, self.lbl_rx, self.lbl_ry, self.lbl_rz]:
            w.setText("--")

    # -------------- Aufräumen --------------
    def closeEvent(self, event):
        self.disconnect_robot()
        return super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    gui = URJogGUI()
    gui.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
