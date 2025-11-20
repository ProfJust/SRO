import sys
import math
import csv
import threading
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtWidgets import (
    QApplication, QWidget, QGridLayout, QPushButton, QLineEdit, QListWidget,
    QDoubleSpinBox, QLabel, QGroupBox, QHBoxLayout, QVBoxLayout, QFileDialog
)

# ur_rtde
try:
    import rtde_control
    import rtde_receive
except ImportError:
    rtde_control = None
    rtde_receive = None


def r2d(rad):
    return math.degrees(rad)


def d2r(deg):
    return math.radians(deg)


class URJogGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UR3e Jog GUI (ur_rtde · TCP Jog + Pose + Teach/Hold)")
        self.setMinimumWidth(860)

        # RTDE handles
        self.rtde_c = None
        self.rtde_r = None
        self.connected = False

        # Jog-Status
        self.current_twist = [0, 0, 0, 0, 0, 0]  # [vx,vy,vz,wx,wy,wz]  m/s, rad/s
        self.jog_active = False
        self.lock = threading.Lock()

        # Teach & Hold
        self.teach_points = []  # list of {"name": str, "pose": [x,y,z,rx,ry,rz]}
        self.hold_active = False
        self.hold_pose = None

        # UI
        self._build_ui()

        # Timer: sendet Jog/Servo und aktualisiert Pose
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
        self.acc_spin.setRange(0.1, 5.0)   # m/s^2 (für speedL und moveL)
        self.acc_spin.setDecimals(2)
        self.acc_spin.setSingleStep(0.1)
        self.acc_spin.setValue(0.5)

        # MoveL Parameter
        self.movel_v_spin = QDoubleSpinBox()
        self.movel_v_spin.setRange(0.001, 0.5)   # m/s
        self.movel_v_spin.setDecimals(3)
        self.movel_v_spin.setSingleStep(0.01)
        self.movel_v_spin.setValue(0.05)

        self.movel_a_spin = QDoubleSpinBox()
        self.movel_a_spin.setRange(0.1, 5.0)     # m/s^2
        self.movel_a_spin.setDecimals(2)
        self.movel_a_spin.setSingleStep(0.1)
        self.movel_a_spin.setValue(0.5)

        # ServoL Parameter (für Hold)
        self.servo_a_spin = QDoubleSpinBox()
        self.servo_a_spin.setRange(0.1, 10.0)
        self.servo_a_spin.setDecimals(2)
        self.servo_a_spin.setSingleStep(0.1)
        self.servo_a_spin.setValue(1.2)

        self.servo_v_spin = QDoubleSpinBox()
        self.servo_v_spin.setRange(0.01, 1.0)
        self.servo_v_spin.setDecimals(2)
        self.servo_v_spin.setSingleStep(0.01)
        self.servo_v_spin.setValue(0.25)

        self.servo_lookahead_spin = QDoubleSpinBox()
        self.servo_lookahead_spin.setRange(0.01, 0.2)
        self.servo_lookahead_spin.setDecimals(3)
        self.servo_lookahead_spin.setSingleStep(0.005)
        self.servo_lookahead_spin.setValue(0.10)

        self.servo_gain_spin = QDoubleSpinBox()
        self.servo_gain_spin.setRange(1.0, 3000.0)
        self.servo_gain_spin.setDecimals(1)
        self.servo_gain_spin.setSingleStep(10.0)
        self.servo_gain_spin.setValue(300.0)

        param_layout.addWidget(QLabel("Linear v [m/s]:"), 0, 0)
        param_layout.addWidget(self.lin_speed_spin, 0, 1)
        param_layout.addWidget(QLabel("Angular ω [rad/s]:"), 0, 2)
        param_layout.addWidget(self.ang_speed_spin, 0, 3)
        param_layout.addWidget(QLabel("Jog Beschl. [m/s²]:"), 1, 0)
        param_layout.addWidget(self.acc_spin, 1, 1)

        param_layout.addWidget(QLabel("moveL v [m/s]:"), 2, 0)
        param_layout.addWidget(self.movel_v_spin, 2, 1)
        param_layout.addWidget(QLabel("moveL a [m/s²]:"), 2, 2)
        param_layout.addWidget(self.movel_a_spin, 2, 3)

        param_layout.addWidget(QLabel("servoL a:"), 3, 0)
        param_layout.addWidget(self.servo_a_spin, 3, 1)
        param_layout.addWidget(QLabel("servoL v:"), 3, 2)
        param_layout.addWidget(self.servo_v_spin, 3, 3)
        param_layout.addWidget(QLabel("servoL lookahead [s]:"), 4, 0)
        param_layout.addWidget(self.servo_lookahead_spin, 4, 1)
        param_layout.addWidget(QLabel("servoL gain:"), 4, 2)
        param_layout.addWidget(self.servo_gain_spin, 4, 3)

        param_box.setLayout(param_layout)
        main.addWidget(param_box)

        # Zweispaltiges Layout: Links Jog, rechts Teach/Hold
        two_col = QHBoxLayout()
        main.addLayout(two_col)

        # ---- Linke Spalte: Jog ----
        jog_col = QVBoxLayout()

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
            b.setMinimumHeight(44)
        grid_lin.addWidget(self.btn_xp, 0, 0)
        grid_lin.addWidget(self.btn_yp, 0, 1)
        grid_lin.addWidget(self.btn_zp, 0, 2)
        grid_lin.addWidget(self.btn_xm, 1, 0)
        grid_lin.addWidget(self.btn_ym, 1, 1)
        grid_lin.addWidget(self.btn_zm, 1, 2)
        jog_lin_box.setLayout(grid_lin)
        jog_col.addWidget(jog_lin_box)

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
            b.setMinimumHeight(44)
        grid_rot.addWidget(self.btn_rxp, 0, 0)
        grid_rot.addWidget(self.btn_ryp, 0, 1)
        grid_rot.addWidget(self.btn_rzp, 0, 2)
        grid_rot.addWidget(self.btn_rxm, 1, 0)
        grid_rot.addWidget(self.btn_rym, 1, 1)
        grid_rot.addWidget(self.btn_rzm, 1, 2)
        jog_rot_box.setLayout(grid_rot)
        jog_col.addWidget(jog_rot_box)

        # Pose Anzeige
        pose_box = QGroupBox("Aktuelle TCP-Pose")
        pose_grid = QGridLayout()
        self.lbl_x = QLabel("--"); self.lbl_y = QLabel("--"); self.lbl_z = QLabel("--")
        self.lbl_rx = QLabel("--"); self.lbl_ry = QLabel("--"); self.lbl_rz = QLabel("--")
        pose_grid.addWidget(QLabel("X [mm]:"), 0, 0); pose_grid.addWidget(self.lbl_x, 0, 1)
        pose_grid.addWidget(QLabel("Y [mm]:"), 0, 2); pose_grid.addWidget(self.lbl_y, 0, 3)
        pose_grid.addWidget(QLabel("Z [mm]:"), 0, 4); pose_grid.addWidget(self.lbl_z, 0, 5)
        pose_grid.addWidget(QLabel("Rx [°]:"), 1, 0); pose_grid.addWidget(self.lbl_rx, 1, 1)
        pose_grid.addWidget(QLabel("Ry [°]:"), 1, 2); pose_grid.addWidget(self.lbl_ry, 1, 3)
        pose_grid.addWidget(QLabel("Rz [°]:"), 1, 4); pose_grid.addWidget(self.lbl_rz, 1, 5)
        pose_box.setLayout(pose_grid)
        jog_col.addWidget(pose_box)

        two_col.addLayout(jog_col, 1)

        # ---- Rechte Spalte: Teach & Hold ----
        teach_col = QVBoxLayout()
        teach_box = QGroupBox("Teach-Punkte")
        teach_layout = QVBoxLayout()

        name_row = QHBoxLayout()
        self.teach_name_edit = QLineEdit()
        self.teach_name_edit.setPlaceholderText("Name des Teach-Punkts (z. B. P1)")
        self.btn_teach_here = QPushButton("Teach: aktuelle Pose speichern")
        name_row.addWidget(self.teach_name_edit)
        name_row.addWidget(self.btn_teach_here)
        teach_layout.addLayout(name_row)

        self.list_teach = QListWidget()
        teach_layout.addWidget(self.list_teach)

        teach_btn_row = QHBoxLayout()
        self.btn_move_to = QPushButton("Anfahren (moveL)")
        self.btn_set_hold_from_sel = QPushButton("Hold-Ziel = Auswahl")
        self.btn_delete = QPushButton("Löschen")
        teach_btn_row.addWidget(self.btn_move_to)
        teach_btn_row.addWidget(self.btn_set_hold_from_sel)
        teach_btn_row.addWidget(self.btn_delete)
        teach_layout.addLayout(teach_btn_row)

        # CSV Save/Load
        csv_row = QHBoxLayout()
        self.btn_save_csv = QPushButton("CSV speichern")
        self.btn_load_csv = QPushButton("CSV laden")
        csv_row.addWidget(self.btn_save_csv); csv_row.addWidget(self.btn_load_csv)
        teach_layout.addLayout(csv_row)

        teach_box.setLayout(teach_layout)
        teach_col.addWidget(teach_box)

        hold_box = QGroupBox("Pose-Hold")
        hold_layout = QGridLayout()
        self.btn_hold_toggle = QPushButton("Hold AUS")
        self.btn_hold_toggle.setCheckable(True)
        self.btn_hold_from_current = QPushButton("Hold-Ziel = aktuelle Pose")
        self.lbl_hold_target = QLabel("Ziel: —")
        hold_layout.addWidget(self.btn_hold_toggle, 0, 0)
        hold_layout.addWidget(self.btn_hold_from_current, 0, 1)
        hold_layout.addWidget(QLabel("Aktuelles Hold-Ziel:"), 1, 0)
        hold_layout.addWidget(self.lbl_hold_target, 1, 1)
        hold_box.setLayout(hold_layout)
        teach_col.addWidget(hold_box)

        two_col.addLayout(teach_col, 1)

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

        # Jog Buttons → press & hold
        self._wire_hold_button(self.btn_xp, axis=0, sign=+1, rotational=False)
        self._wire_hold_button(self.btn_xm, axis=0, sign=-1, rotational=False)
        self._wire_hold_button(self.btn_yp, axis=1, sign=+1, rotational=False)
        self._wire_hold_button(self.btn_ym, axis=1, sign=-1, rotational=False)
        self._wire_hold_button(self.btn_zp, axis=2, sign=+1, rotational=False)
        self._wire_hold_button(self.btn_zm, axis=2, sign=-1, rotational=False)
        self._wire_hold_button(self.btn_rxp, axis=3, sign=+1, rotational=True)
        self._wire_hold_button(self.btn_rxm, axis=3, sign=-1, rotational=True)
        self._wire_hold_button(self.btn_ryp, axis=4, sign=+1, rotational=True)
        self._wire_hold_button(self.btn_rym, axis=4, sign=-1, rotational=True)
        self._wire_hold_button(self.btn_rzp, axis=5, sign=+1, rotational=True)
        self._wire_hold_button(self.btn_rzm, axis=5, sign=-1, rotational=True)

        # Teach/Hold Actions
        self.btn_teach_here.clicked.connect(self._teach_current_pose)
        self.btn_move_to.clicked.connect(self._move_to_selected)
        self.btn_delete.clicked.connect(self._delete_selected)
        self.btn_set_hold_from_sel.clicked.connect(self._set_hold_from_selected)
        self.btn_hold_toggle.toggled.connect(self._toggle_hold)
        self.btn_hold_from_current.clicked.connect(self._set_hold_from_current)
        self.btn_save_csv.clicked.connect(self._save_csv)
        self.btn_load_csv.clicked.connect(self._load_csv)

        self._set_controls_enabled(False)

    def _wire_hold_button(self, btn: QPushButton, axis: int, sign: int, rotational: bool):
        btn.pressed.connect(lambda: self._start_jog(axis, sign, rotational))
        btn.released.connect(self._stop_jog)

    def _set_controls_enabled(self, enabled: bool):
        widgets = [
            self.btn_xp, self.btn_xm, self.btn_yp, self.btn_ym, self.btn_zp, self.btn_zm,
            self.btn_rxp, self.btn_rxm, self.btn_ryp, self.btn_rym, self.btn_rzp, self.btn_rzm,
            self.estop_btn, self.btn_teach_here, self.btn_move_to, self.btn_delete,
            self.btn_hold_toggle, self.btn_hold_from_current, self.btn_set_hold_from_sel,
            self.btn_save_csv, self.btn_load_csv
        ]
        for w in widgets:
            w.setEnabled(enabled)

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
        self._disable_hold()
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
        # Hold aus, sobald man manuell joggt
        self._disable_hold()
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
        # Not-Aus (softwareseitig): stoppe Jog & Hold
        self._stop_jog()
        self._disable_hold()

    # -------------- Teach --------------
    def _teach_current_pose(self):
        if not self.connected or self.rtde_r is None:
            return
        name = self.teach_name_edit.text().strip() or f"P{len(self.teach_points)+1}"
        pose = self.rtde_r.getActualTCPPose()  # [x,y,z,rx,ry,rz] (m, rad)
        if not pose or len(pose) != 6:
            QtWidgets.QMessageBox.warning(self, "Warnung", "Konnte aktuelle Pose nicht lesen.")
            return
        entry = {"name": name, "pose": [float(p) for p in pose]}
        self.teach_points.append(entry)
        self._refresh_teach_list()
        self.teach_name_edit.clear()

    def _refresh_teach_list(self):
        self.list_teach.clear()
        for tp in self.teach_points:
            x, y, z, rx, ry, rz = tp["pose"]
            mm = [x*1000, y*1000, z*1000]
            deg = [r2d(rx), r2d(ry), r2d(rz)]
            self.list_teach.addItem(f'{tp["name"]}: '
                                    f'X={mm[0]:.1f}mm Y={mm[1]:.1f}mm Z={mm[2]:.1f}mm | '
                                    f'Rx={deg[0]:.1f}° Ry={deg[1]:.1f}° Rz={deg[2]:.1f}°')

    def _selected_teach_index(self):
        row = self.list_teach.currentRow()
        if 0 <= row < len(self.teach_points):
            return row
        return None

    def _move_to_selected(self):
        if not self.connected or self.rtde_c is None:
            return
        idx = self._selected_teach_index()
        if idx is None:
            QtWidgets.QMessageBox.information(self, "Info", "Bitte einen Teach-Punkt auswählen.")
            return
        # Hold ausschalten für saubere Bewegung
        self._disable_hold()
        target = list(self.teach_points[idx]["pose"])
        v = self.movel_v_spin.value()
        a = self.movel_a_spin.value()
        try:
            # Blocking moveL – Achtung: blockiert GUI nicht, da RTDE intern blockierend ist,
            # aber Aufruf in GUI-Thread ist für kurze Bewegungen ok. Für lange Trajektorien -> Thread.
            self.rtde_c.moveL(target, a, v)  # blend=0, async=False (default)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "moveL Fehler", str(e))

    def _delete_selected(self):
        idx = self._selected_teach_index()
        if idx is None:
            return
        self.teach_points.pop(idx)
        self._refresh_teach_list()

    # -------------- Hold --------------
    def _set_hold_from_selected(self):
        idx = self._selected_teach_index()
        if idx is None:
            QtWidgets.QMessageBox.information(self, "Info", "Bitte einen Teach-Punkt auswählen.")
            return
        self.hold_pose = list(self.teach_points[idx]["pose"])
        self.lbl_hold_target.setText(self.teach_points[idx]["name"])

    def _set_hold_from_current(self):
        if not self.connected or self.rtde_r is None:
            return
        pose = self.rtde_r.getActualTCPPose()
        if pose and len(pose) == 6:
            self.hold_pose = list(pose)
            self.lbl_hold_target.setText("aktuelle Pose")
        else:
            QtWidgets.QMessageBox.warning(self, "Warnung", "Konnte aktuelle Pose nicht lesen.")

    def _toggle_hold(self, checked: bool):
        if checked:
            if self.hold_pose is None:
                QtWidgets.QMessageBox.information(self, "Info", "Kein Hold-Ziel gesetzt.")
                self.btn_hold_toggle.setChecked(False)
                return
            # Beim Aktivieren Jog stoppen
            self._stop_jog()
            self.hold_active = True
            self.btn_hold_toggle.setText("Hold EIN")
        else:
            self._disable_hold()

    def _disable_hold(self):
        self.hold_active = False
        self.btn_hold_toggle.setChecked(False)
        self.btn_hold_toggle.setText("Hold AUS")

    # -------------- CSV Save/Load --------------
    def _save_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "CSV speichern", "teach_points.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["name", "x", "y", "z", "rx", "ry", "rz"])  # SI-Einheiten!
                for tp in self.teach_points:
                    row = [tp["name"]] + [f"{v:.9f}" for v in tp["pose"]]
                    w.writerow(row)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "CSV Fehler", str(e))

    def _load_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "CSV laden", "", "CSV (*.csv)")
        if not path:
            return
        try:
            data = []
            with open(path, "r", newline="") as f:
                r = csv.DictReader(f)
                for row in r:
                    pose = [float(row["x"]), float(row["y"]), float(row["z"]),
                            float(row["rx"]), float(row["ry"]), float(row["rz"])]
                    data.append({"name": row["name"], "pose": pose})
            self.teach_points = data
            self._refresh_teach_list()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "CSV Fehler", str(e))

    # -------------- Timer --------------
    def _tick(self):
        """Alle 100 ms: ggf. speedL/servoL senden und Pose aktualisieren."""
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

        # 2) Pose-Hold per servoL (sofern aktiv)
        try:
            if self.hold_active and self.hold_pose and self.rtde_c:
                a = self.servo_a_spin.value()
                v = self.servo_v_spin.value()
                lookahead = self.servo_lookahead_spin.value()
                gain = self.servo_gain_spin.value()
                # t = 0.1 deckt sich mit Timerperiode
                self.rtde_c.servoL(self.hold_pose, a, v, 0.1, lookahead, gain)
        except Exception as e:
            # Bei Fehler Hold deaktivieren
            self._disable_hold()
            self.status_lbl.setText(f"servoL Fehler: {e}")

        # 3) Pose lesen & anzeigen
        try:
            if self.rtde_r:
                pose = self.rtde_r.getActualTCPPose()  # [x,y,z,rx,ry,rz]
                if pose and len(pose) == 6:
                    x_mm = pose[0] * 1000.0
                    y_mm = pose[1] * 1000.0
                    z_mm = pose[2] * 1000.0
                    rx_deg = r2d(pose[3])
                    ry_deg = r2d(pose[4])
                    rz_deg = r2d(pose[5])
                    self.lbl_x.setText(f"{x_mm: .2f}")
                    self.lbl_y.setText(f"{y_mm: .2f}")
                    self.lbl_z.setText(f"{z_mm: .2f}")
                    self.lbl_rx.setText(f"{rx_deg: .2f}")
                    self.lbl_ry.setText(f"{ry_deg: .2f}")
                    self.lbl_rz.setText(f"{rz_deg: .2f}")
        except Exception:
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
