import sys
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
        self.setWindowTitle("UR3e Jog GUI (ur_rtde · TCP Jog)")
        self.setMinimumWidth(520)

        # RTDE handles
        self.rtde_c = None
        self.rtde_r = None
        self.connected = False

        # Jog-Status
        self.current_twist = [0, 0, 0, 0, 0, 0]  # m/s, rad/s
        self.jog_active = False
        self.lock = threading.Lock()

        # UI bauen
        self._build_ui()

        # Timer schickt periodisch speedL
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(100)  # ms -> time=0.1s unten
        self.timer.timeout.connect(self._jog_tick)

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
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.0, 0.5)  # m/s
        self.speed_spin.setDecimals(3)
        self.speed_spin.setSingleStep(0.01)
        self.speed_spin.setValue(0.050)     # 50 mm/s default

        self.acc_spin = QDoubleSpinBox()
        self.acc_spin.setRange(0.1, 5.0)   # m/s^2
        self.acc_spin.setDecimals(2)
        self.acc_spin.setSingleStep(0.1)
        self.acc_spin.setValue(0.5)

        param_layout.addWidget(QLabel("Geschwindigkeit [m/s]:"), 0, 0)
        param_layout.addWidget(self.speed_spin, 0, 1)
        param_layout.addWidget(QLabel("Beschleunigung [m/s²]:"), 0, 2)
        param_layout.addWidget(self.acc_spin, 0, 3)
        param_box.setLayout(param_layout)
        main.addWidget(param_box)

        # Jog Buttons
        jog_box = QGroupBox("Jog (TCP kartesisch)")
        grid = QGridLayout()

        self.btn_xp = QPushButton("+X")
        self.btn_xm = QPushButton("−X")
        self.btn_yp = QPushButton("+Y")
        self.btn_ym = QPushButton("−Y")
        self.btn_zp = QPushButton("+Z")
        self.btn_zm = QPushButton("−Z")

        # Schöne, große Buttons
        for b in [self.btn_xp, self.btn_xm, self.btn_yp, self.btn_ym, self.btn_zp, self.btn_zm]:
            b.setMinimumHeight(56)

        # Layout (2 Zeilen x 3 Spalten)
        grid.addWidget(self.btn_xp, 0, 0)
        grid.addWidget(self.btn_yp, 0, 1)
        grid.addWidget(self.btn_zp, 0, 2)
        grid.addWidget(self.btn_xm, 1, 0)
        grid.addWidget(self.btn_ym, 1, 1)
        grid.addWidget(self.btn_zm, 1, 2)

        jog_box.setLayout(grid)
        main.addWidget(jog_box)

        # Status & Not-Aus (softwareseitig: speedStop)
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

        # Press-and-hold für Jogging
        self._wire_hold_button(self.btn_xp, axis=0, sign=+1)
        self._wire_hold_button(self.btn_xm, axis=0, sign=-1)
        self._wire_hold_button(self.btn_yp, axis=1, sign=+1)
        self._wire_hold_button(self.btn_ym, axis=1, sign=-1)
        self._wire_hold_button(self.btn_zp, axis=2, sign=+1)
        self._wire_hold_button(self.btn_zm, axis=2, sign=-1)

        self._set_jog_enabled(False)

    def _wire_hold_button(self, btn: QPushButton, axis: int, sign: int):
        # gedrückt -> Jog starten; loslassen -> Stop
        btn.pressed.connect(lambda: self._start_jog(axis, sign))
        btn.released.connect(self._stop_jog)

    def _set_jog_enabled(self, enabled: bool):
        for b in [self.btn_xp, self.btn_xm, self.btn_yp, self.btn_ym, self.btn_zp, self.btn_zm]:
            b.setEnabled(enabled)
        self.estop_btn.setEnabled(enabled)

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
            self._set_jog_enabled(True)
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
                # sicher anhalten
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
            self._set_jog_enabled(False)
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            self.status_lbl.setText("Getrennt")

    # -------------- Jogging --------------
    def _start_jog(self, axis: int, sign: int):
        if not self.connected or self.rtde_c is None:
            return
        v = self.speed_spin.value()
        twist = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        twist[axis] = sign * v  # X/Y/Z m/s
        with self.lock:
            self.current_twist = twist
            self.jog_active = True

    def _stop_jog(self):
        with self.lock:
            self.jog_active = False
            self.current_twist = [0, 0, 0, 0, 0, 0]
        try:
            if self.rtde_c:
                # schneller, definierter Stopp der speedL Bewegung
                self.rtde_c.speedStop()
        except Exception:
            pass

    def estop(self):
        # Software-Stopp (setzt speed auf 0)
        self._stop_jog()

    def _jog_tick(self):
        """Wird alle 100 ms aufgerufen – hält speedL ‘lebendig’.
        ur_rtde: speedL(xd, acc, time) → zeitgesteuerter Speed-Befehl.
        Wir rufen das fortlaufend auf, solange Jog aktiv ist.
        """
        if not self.connected or self.rtde_c is None:
            return
        with self.lock:
            jog = self.jog_active
            twist = list(self.current_twist)

        try:
            if jog:
                acc = self.acc_spin.value()
                # time gibt die Gültigkeitsdauer des Kommandos an.
                # Wir erneuern alle 0.1 s (Timer), daher time=0.1
                self.rtde_c.speedL(twist, acc, 0.1)
        except Exception as e:
            # Bei Fehlern Jog beenden
            self._stop_jog()
            self.status_lbl.setText(f"Fehler: {e}")

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
