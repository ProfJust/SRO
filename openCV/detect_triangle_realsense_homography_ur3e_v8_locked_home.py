"""
RealSense Dreieckserkennung mit ROI, Homographie und optionaler UR3e/Robotiq-Ansteuerung.

Tabs:
1) Live-Erkennung: RGB-Gesamtbild, HSV-Maske, ROI-Auswertung, Greifwinkel
2) Homographie: Pixelpunkte anklicken, Weltkoordinaten eintragen, H berechnen/speichern/laden, Freedrive ein/aus
3) UR3e + Robotiq: Verbindung, Open/Close, sichere Pick-Bewegung mit UR_RTDE

Version v8:
- Zielpose wird beim Klick auf einen Fahr-/Pick-Button eingefroren.
  Danach beeinflusst eine verdeckte Kamera/das verdeckte Objekt die laufende Bewegung nicht mehr.
- Home-Button fuer UR3e ergaenzt.
- TCP-Orientierung wird standardmaessig aus aktueller Roboterpose uebernommen.
- IK-Vorpruefung vor moveL, um Gelenkgrenzen/Singularitaeten frueh zu erkennen.
- Hinweis: UR-Pose [x,y,z,rx,ry,rz] verwendet Rotationsvektor, nicht Euler-RPY.

SICHERHEIT:
- Robotermodus ist standardmaessig deaktiviert.
- Erst IPs pruefen, Roboter freifahren, niedrige Geschwindigkeit verwenden.
- Testen Sie zuerst ohne Objekt und mit grossem Abstand zur Ebene.
"""

import sys
import os
import json
import math
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np
import pyrealsense2 as rs
from PyQt6 import QtCore, QtGui, QtWidgets

# optionale Robotik-Imports
try:
    import rtde_control
    import rtde_receive
except Exception:
    rtde_control = None
    rtde_receive = None

try:
    from robotiq_gripper import RobotiqGripper
except Exception:
    RobotiqGripper = None


# ============================================================
# Einstellungen
# ============================================================

CAM_WIDTH = 640
CAM_HEIGHT = 480
CAM_FPS = 6

# ROI im Gesamtbild: linke obere Ecke + Breite/Hoehe
ROI_X = 260
ROI_Y = 120
ROI_W = 260
ROI_H = 220

# HSV-Grenzen fuer das gruene Dreieck, OpenCV: H 0..179, S/V 0..255
HSV_LOWER = np.array([38, 80, 50], dtype=np.uint8)
HSV_UPPER = np.array([60, 255, 220], dtype=np.uint8)

MIN_AREA = 300
APPROX_EPS_FACTOR = 0.04
GRASP_SHIFT_FACTOR = 0.15

# Winkel-Offset Kamera -> UR3e-Basis, muss kalibriert werden
CAMERA_TO_ROBOT_YAW_OFFSET_DEG = 0.0

# Fallback Pixel->Welt, wenn keine Homographie geladen/berechnet ist
MM_PER_PIXEL_X = 1.0
MM_PER_PIXEL_Y = 1.0
WORLD_X_OFFSET_MM = 0.0
WORLD_Y_OFFSET_MM = 0.0

# Winkelglaettung: kleiner = ruhiger, aber traeger
ANGLE_FILTER_ALPHA = 0.20

# UR/Gripper Defaultwerte
DEFAULT_UR_IP = "192.168.0.17"
DEFAULT_GRIPPER_IP = "192.168.0.17"
DEFAULT_GRIPPER_PORT = 63352
DEFAULT_TCP_Z_M = 0.090     # Greifhoehe ueber Roboterbasis/Arbeitsebene, ANPASSEN!
DEFAULT_APPROACH_M = 0.060   # Sicherheitsabstand ueber Greifhoehe
DEFAULT_SPEED = 0.04
DEFAULT_ACCEL = 0.05

# Home-Position als Gelenkwinkel in Grad.
# Bitte an Ihren Laboraufbau anpassen und zuerst langsam testen.
# Reihenfolge: Base, Shoulder, Elbow, Wrist1, Wrist2, Wrist3
DEFAULT_HOME_Q_DEG = [0.0, -90.0, 90.0, -90.0, -90.0, 0.0]
DEFAULT_HOME_SPEED = 0.30
DEFAULT_HOME_ACCEL = 0.20

DEFAULT_RX = math.pi         # Beispiel: Werkzeug zeigt nach unten. Muss ggf. angepasst werden.
DEFAULT_RY = 0.0
DEFAULT_RZ_OFFSET = 0.0

HOMOGRAPHY_FILE = "homography_triangle_ur3e.json"


# ============================================================
# Datenstrukturen
# ============================================================

@dataclass
class DetectionResult:
    cx_roi: int
    cy_roi: int
    gx_roi: int
    gy_roi: int
    edge_angle_deg: float
    edge_angle_raw_deg: float
    closing_direction_deg: float
    yaw_ur3e_deg: float
    area: float
    num_points: int


# ============================================================
# Bildverarbeitung
# ============================================================

filtered_angle: Optional[float] = None


def normalize_angle_180(angle_deg: float) -> float:
    angle_deg = angle_deg % 180.0
    if angle_deg < 0:
        angle_deg += 180.0
    return angle_deg


def normalize_angle_360(angle_deg: float) -> float:
    angle_deg = angle_deg % 360.0
    if angle_deg < 0:
        angle_deg += 360.0
    return angle_deg


def smooth_angle_180(angle_deg: float) -> float:
    """Exponentieller Filter fuer Winkel mit 180-Grad-Periodizitaet."""
    global filtered_angle
    angle_deg = normalize_angle_180(angle_deg)

    if filtered_angle is None:
        filtered_angle = angle_deg
        return filtered_angle

    diff = angle_deg - filtered_angle
    while diff > 90.0:
        diff -= 180.0
    while diff < -90.0:
        diff += 180.0

    filtered_angle = normalize_angle_180(filtered_angle + ANGLE_FILTER_ALPHA * diff)
    return filtered_angle


def create_mask_bgr(img_bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, HSV_LOWER, HSV_UPPER)
    kernel = np.ones((7, 7), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def get_longest_edge(points: np.ndarray):
    edges = []
    n = len(points)
    for i in range(n):
        p1 = points[i]
        p2 = points[(i + 1) % n]
        length = float(np.linalg.norm(p2 - p1))
        edges.append((length, p1, p2))
    return max(edges, key=lambda e: e[0])


def detect_triangle_in_roi(roi_bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray, Optional[DetectionResult]]:
    mask = create_mask_bgr(roi_bgr)
    eval_img = roi_bgr.copy()

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return eval_img, mask, None

    cnt = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(cnt)
    if area < MIN_AREA:
        return eval_img, mask, None

    M = cv2.moments(cnt)
    if M["m00"] == 0:
        return eval_img, mask, None

    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])

    epsilon = APPROX_EPS_FACTOR * cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, epsilon, True)
    points = approx.reshape(-1, 2)
    if len(points) < 3:
        return eval_img, mask, None

    _, p1, p2 = get_longest_edge(points)
    dx = int(p2[0] - p1[0])
    dy = int(p2[1] - p1[1])
    edge_angle_deg_raw = normalize_angle_180(math.degrees(math.atan2(dy, dx)))
    edge_angle_deg = smooth_angle_180(edge_angle_deg_raw)

    closing_direction_deg = normalize_angle_180(edge_angle_deg + 90.0)
    yaw_ur3e_deg = normalize_angle_180(edge_angle_deg + CAMERA_TO_ROBOT_YAW_OFFSET_DEG)

    edge_mid = ((p1.astype(float) + p2.astype(float)) / 2.0)
    center = np.array([cx, cy], dtype=float)
    grasp = center + GRASP_SHIFT_FACTOR * (edge_mid - center)
    gx = int(round(grasp[0]))
    gy = int(round(grasp[1]))

    # Visualisierung
    cv2.drawContours(eval_img, [cnt], -1, (0, 255, 0), 2)
    cv2.polylines(eval_img, [points.astype(np.int32)], True, (255, 0, 255), 2)
    cv2.line(eval_img, tuple(p1), tuple(p2), (255, 255, 0), 4)
    cv2.circle(eval_img, (cx, cy), 6, (255, 0, 0), -1)    # Schwerpunkt
    cv2.circle(eval_img, (gx, gy), 6, (0, 0, 255), -1)     # Greifpunkt

    length = 70
    a = math.radians(closing_direction_deg)
    x2 = int(gx + length * math.cos(a))
    y2 = int(gy + length * math.sin(a))
    cv2.arrowedLine(eval_img, (gx, gy), (x2, y2), (0, 255, 255), 3, tipLength=0.25)

    cv2.putText(eval_img, f"Kante: {edge_angle_deg:.1f} deg", (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 0, 255), 2, cv2.LINE_AA)
    cv2.putText(eval_img, f"UR3e Yaw: {yaw_ur3e_deg:.1f} deg", (10, 55),
                cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 0, 255), 2, cv2.LINE_AA)

    return eval_img, mask, DetectionResult(
        cx_roi=cx, cy_roi=cy, gx_roi=gx, gy_roi=gy,
        edge_angle_deg=edge_angle_deg,
        edge_angle_raw_deg=edge_angle_deg_raw,
        closing_direction_deg=closing_direction_deg,
        yaw_ur3e_deg=yaw_ur3e_deg,
        area=area,
        num_points=len(points),
    )


def resize(img: np.ndarray, scale: float) -> np.ndarray:
    if scale == 1.0:
        return img
    return cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)


def draw_text_line(img: np.ndarray, text: str, x: int, y: int,
                   scale: float = 0.55, color=(255, 255, 255), thickness: int = 1):
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                scale, color, thickness, cv2.LINE_AA)


def bgr_to_qpixmap(img_bgr: np.ndarray) -> QtGui.QPixmap:
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    qimg = QtGui.QImage(rgb.data, w, h, ch * w, QtGui.QImage.Format.Format_RGB888)
    return QtGui.QPixmap.fromImage(qimg.copy())


# ============================================================
# Homographie
# ============================================================

class HomographyModel:
    def __init__(self):
        self.pixel_points: list[tuple[float, float]] = []
        self.world_points: list[tuple[float, float]] = []
        self.H: Optional[np.ndarray] = None

    def clear(self):
        self.pixel_points.clear()
        self.world_points.clear()
        self.H = None

    def is_valid(self) -> bool:
        return self.H is not None

    def compute(self) -> bool:
        if len(self.pixel_points) < 4 or len(self.world_points) < 4:
            return False
        src = np.array(self.pixel_points, dtype=np.float32)
        dst = np.array(self.world_points, dtype=np.float32)
        H, _ = cv2.findHomography(src, dst, method=0)
        if H is None:
            return False
        self.H = H
        return True

    def pixel_to_world(self, u: float, v: float) -> tuple[float, float]:
        if self.H is None:
            x_mm = WORLD_X_OFFSET_MM + u * MM_PER_PIXEL_X
            y_mm = WORLD_Y_OFFSET_MM + v * MM_PER_PIXEL_Y
            return x_mm, y_mm
        p = np.array([[[float(u), float(v)]]], dtype=np.float32)
        w = cv2.perspectiveTransform(p, self.H)[0, 0]
        return float(w[0]), float(w[1])

    def save(self, path: str):
        data = {
            "pixel_points": self.pixel_points,
            "world_points": self.world_points,
            "H": self.H.tolist() if self.H is not None else None,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str) -> bool:
        if not os.path.exists(path):
            return False
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.pixel_points = [tuple(p) for p in data.get("pixel_points", [])]
        self.world_points = [tuple(p) for p in data.get("world_points", [])]
        H = data.get("H")
        self.H = np.array(H, dtype=np.float64) if H is not None else None
        return self.H is not None


# ============================================================
# GUI-Elemente
# ============================================================

class ImageLabel(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal(int, int)

    def __init__(self, title=""):
        super().__init__()
        self.title = title
        self.setMinimumSize(320, 240)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: black; color: white;")
        self._last_pixmap_size = None
        self._source_size = None

    def set_cv_image(self, img_bgr: np.ndarray):
        self._source_size = (img_bgr.shape[1], img_bgr.shape[0])
        pix = bgr_to_qpixmap(img_bgr)
        scaled = pix.scaled(self.size(), QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                            QtCore.Qt.TransformationMode.SmoothTransformation)
        self._last_pixmap_size = (scaled.width(), scaled.height())
        self.setPixmap(scaled)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if self._source_size is None or self._last_pixmap_size is None:
            return
        src_w, src_h = self._source_size
        pix_w, pix_h = self._last_pixmap_size
        off_x = (self.width() - pix_w) / 2
        off_y = (self.height() - pix_h) / 2
        x = event.position().x() - off_x
        y = event.position().y() - off_y
        if x < 0 or y < 0 or x >= pix_w or y >= pix_h:
            return
        u = int(round(x * src_w / pix_w))
        v = int(round(y * src_h / pix_h))
        self.clicked.emit(u, v)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RealSense Dreieckserkennung + Homographie + UR3e/Robotiq")
        self.resize(1300, 850)

        self.pipeline = None
        self.last_frame: Optional[np.ndarray] = None
        self.last_roi: Optional[np.ndarray] = None
        self.last_eval: Optional[np.ndarray] = None
        self.last_mask: Optional[np.ndarray] = None
        self.last_result: Optional[DetectionResult] = None

        self.homography = HomographyModel()
        self.homography.load(HOMOGRAPHY_FILE)

        self.rtde_c = None
        self.rtde_r = None
        self.gripper = None

        # Eingefrorene Zielpose: wird beim Klick auf Fahren/Pick gespeichert,
        # damit eine spaeter verdeckte Kamera das laufende Ziel nicht veraendert.
        self.locked_target_pose: Optional[list[float]] = None
        self.locked_approach_pose: Optional[list[float]] = None

        # Freedrive/Teach-Mode-Zustand
        self.freedrive_enabled = False
        self.freedrive_blink_on = False
        self.freedrive_blink_timer = QtCore.QTimer(self)
        self.freedrive_blink_timer.timeout.connect(self._blink_freedrive_button)

        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)
        self._build_live_tab()
        self._build_homography_tab()
        self._build_robot_tab()

        self._start_realsense()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    # ---------------- Live-Tab ----------------
    def _build_live_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(tab)

        self.lbl_overview = ImageLabel("RGB-Gesamtbild")
        self.lbl_mask = ImageLabel("HSV-Maske")
        self.lbl_eval = ImageLabel("ROI-Auswertung")
        self.status_live = QtWidgets.QTextEdit()
        self.status_live.setReadOnly(True)
        self.status_live.setMaximumHeight(90)

        layout.addWidget(QtWidgets.QLabel("RGB-Gesamtbild mit ROI"), 0, 0)
        layout.addWidget(QtWidgets.QLabel("HSV-Maske"), 0, 1)
        layout.addWidget(self.lbl_overview, 1, 0)
        layout.addWidget(self.lbl_mask, 1, 1)
        layout.addWidget(QtWidgets.QLabel("ROI-Auswertung"), 2, 0, 1, 2)
        layout.addWidget(self.lbl_eval, 3, 0, 1, 2)
        layout.addWidget(self.status_live, 4, 0, 1, 2)
        layout.setRowStretch(1, 1)
        layout.setRowStretch(3, 2)

        self.tabs.addTab(tab, "1 Live-Erkennung")

    # ---------------- Homographie-Tab ----------------
    def _build_homography_tab(self):
        tab = QtWidgets.QWidget()
        main = QtWidgets.QHBoxLayout(tab)

        left = QtWidgets.QVBoxLayout()
        self.lbl_homography_img = ImageLabel("Homographie-Bild")
        self.lbl_homography_img.clicked.connect(self.on_homography_image_clicked)
        left.addWidget(QtWidgets.QLabel("Zum Einlernen vier Referenzpunkte im Bild anklicken."))
        left.addWidget(self.lbl_homography_img)
        main.addLayout(left, stretch=2)

        right = QtWidgets.QVBoxLayout()
        form = QtWidgets.QFormLayout()
        self.spin_world_x = QtWidgets.QDoubleSpinBox()
        self.spin_world_x.setRange(-2000, 2000)
        self.spin_world_x.setDecimals(2)
        self.spin_world_x.setSuffix(" mm")
        self.spin_world_y = QtWidgets.QDoubleSpinBox()
        self.spin_world_y.setRange(-2000, 2000)
        self.spin_world_y.setDecimals(2)
        self.spin_world_y.setSuffix(" mm")
        form.addRow("Welt X fuer naechsten Klick", self.spin_world_x)
        form.addRow("Welt Y fuer naechsten Klick", self.spin_world_y)
        right.addLayout(form)

        self.table_h = QtWidgets.QTableWidget(0, 4)
        self.table_h.setHorizontalHeaderLabels(["u Pixel", "v Pixel", "X mm", "Y mm"])
        self.table_h.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        right.addWidget(self.table_h)

        btns = QtWidgets.QGridLayout()
        self.btn_h_compute = QtWidgets.QPushButton("Homographie berechnen")
        self.btn_h_clear = QtWidgets.QPushButton("Punkte loeschen")
        self.btn_h_save = QtWidgets.QPushButton("Speichern")
        self.btn_h_load = QtWidgets.QPushButton("Laden")
        self.btn_h_compute.clicked.connect(self.compute_homography)
        self.btn_h_clear.clicked.connect(self.clear_homography)
        self.btn_h_save.clicked.connect(self.save_homography)
        self.btn_h_load.clicked.connect(self.load_homography)

        self.btn_freedrive = QtWidgets.QPushButton("Freedrive EIN")
        self.btn_freedrive.setToolTip("UR3e in den Freedrive/Teach Mode setzen. Erneut klicken zum Beenden.")
        self.btn_freedrive.clicked.connect(self.toggle_freedrive)

        btns.addWidget(self.btn_h_compute, 0, 0)
        btns.addWidget(self.btn_h_clear, 0, 1)
        btns.addWidget(self.btn_h_save, 1, 0)
        btns.addWidget(self.btn_h_load, 1, 1)
        btns.addWidget(self.btn_freedrive, 2, 0, 1, 2)
        right.addLayout(btns)

        self.status_h = QtWidgets.QTextEdit()
        self.status_h.setReadOnly(True)
        self.status_h.setPlainText("Homographie: Noch nicht berechnet/geladen." if not self.homography.is_valid() else "Homographie geladen.")
        right.addWidget(self.status_h)
        main.addLayout(right, stretch=1)

        self.tabs.addTab(tab, "2 Homographie")

    # ---------------- Robot-Tab ----------------
    def _build_robot_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        box_conn = QtWidgets.QGroupBox("Verbindung")
        form = QtWidgets.QFormLayout(box_conn)
        self.edit_ur_ip = QtWidgets.QLineEdit(DEFAULT_UR_IP)
        self.edit_gripper_ip = QtWidgets.QLineEdit(DEFAULT_GRIPPER_IP)
        self.spin_gripper_port = QtWidgets.QSpinBox()
        self.spin_gripper_port.setRange(1, 65535)
        self.spin_gripper_port.setValue(DEFAULT_GRIPPER_PORT)
        form.addRow("UR3e IP", self.edit_ur_ip)
        form.addRow("Robotiq IP", self.edit_gripper_ip)
        form.addRow("Robotiq Port", self.spin_gripper_port)
        layout.addWidget(box_conn)

        row_conn = QtWidgets.QHBoxLayout()
        self.btn_connect_ur = QtWidgets.QPushButton("UR_RTDE verbinden")
        self.btn_disconnect_ur = QtWidgets.QPushButton("UR trennen")
        self.btn_connect_gripper = QtWidgets.QPushButton("Gripper verbinden/aktivieren")
        self.btn_gripper_open = QtWidgets.QPushButton("Gripper oeffnen")
        self.btn_gripper_close = QtWidgets.QPushButton("Gripper schliessen")
        self.btn_connect_ur.clicked.connect(self.connect_ur)
        self.btn_disconnect_ur.clicked.connect(self.disconnect_ur)
        self.btn_connect_gripper.clicked.connect(self.connect_gripper)
        self.btn_gripper_open.clicked.connect(lambda: self.move_gripper(0))
        self.btn_gripper_close.clicked.connect(lambda: self.move_gripper(180))
        for b in [self.btn_connect_ur, self.btn_disconnect_ur, self.btn_connect_gripper, self.btn_gripper_open, self.btn_gripper_close]:
            row_conn.addWidget(b)
        layout.addLayout(row_conn)

        box_pose = QtWidgets.QGroupBox("Greifpose / Sicherheitsparameter")
        form2 = QtWidgets.QFormLayout(box_pose)
        self.spin_z = QtWidgets.QDoubleSpinBox(); self.spin_z.setRange(-1.0, 1.5); self.spin_z.setDecimals(4); self.spin_z.setSingleStep(0.005); self.spin_z.setValue(DEFAULT_TCP_Z_M); self.spin_z.setSuffix(" m")
        self.spin_approach = QtWidgets.QDoubleSpinBox(); self.spin_approach.setRange(0.0, 0.5); self.spin_approach.setDecimals(4); self.spin_approach.setSingleStep(0.005); self.spin_approach.setValue(DEFAULT_APPROACH_M); self.spin_approach.setSuffix(" m")
        self.spin_speed = QtWidgets.QDoubleSpinBox(); self.spin_speed.setRange(0.001, 0.5); self.spin_speed.setDecimals(3); self.spin_speed.setValue(DEFAULT_SPEED); self.spin_speed.setSuffix(" m/s")
        self.spin_accel = QtWidgets.QDoubleSpinBox(); self.spin_accel.setRange(0.001, 1.0); self.spin_accel.setDecimals(3); self.spin_accel.setValue(DEFAULT_ACCEL); self.spin_accel.setSuffix(" m/s²")
        self.spin_rx = QtWidgets.QDoubleSpinBox(); self.spin_rx.setRange(-math.pi, math.pi); self.spin_rx.setDecimals(4); self.spin_rx.setValue(DEFAULT_RX)
        self.spin_ry = QtWidgets.QDoubleSpinBox(); self.spin_ry.setRange(-math.pi, math.pi); self.spin_ry.setDecimals(4); self.spin_ry.setValue(DEFAULT_RY)
        self.spin_rz_offset = QtWidgets.QDoubleSpinBox(); self.spin_rz_offset.setRange(-math.pi, math.pi); self.spin_rz_offset.setDecimals(4); self.spin_rz_offset.setValue(DEFAULT_RZ_OFFSET)
        form2.addRow("Greif-Z TCP", self.spin_z)
        form2.addRow("Anfahrhoehe ueber Greif-Z", self.spin_approach)
        form2.addRow("Geschwindigkeit", self.spin_speed)
        form2.addRow("Beschleunigung", self.spin_accel)

        self.edit_home_q = QtWidgets.QLineEdit(", ".join(f"{v:.1f}" for v in DEFAULT_HOME_Q_DEG))
        self.edit_home_q.setToolTip("Home-Gelenkwinkel in Grad: q0, q1, q2, q3, q4, q5")
        self.spin_home_speed = QtWidgets.QDoubleSpinBox(); self.spin_home_speed.setRange(0.01, 1.0); self.spin_home_speed.setDecimals(2); self.spin_home_speed.setValue(DEFAULT_HOME_SPEED); self.spin_home_speed.setSuffix(" rad/s")
        self.spin_home_accel = QtWidgets.QDoubleSpinBox(); self.spin_home_accel.setRange(0.01, 2.0); self.spin_home_accel.setDecimals(2); self.spin_home_accel.setValue(DEFAULT_HOME_ACCEL); self.spin_home_accel.setSuffix(" rad/s²")
        form2.addRow("Home q [deg]", self.edit_home_q)
        form2.addRow("Home Speed", self.spin_home_speed)
        form2.addRow("Home Accel", self.spin_home_accel)

        form2.addRow("RX fest", self.spin_rx)
        form2.addRow("RY fest", self.spin_ry)
        form2.addRow("RZ Offset", self.spin_rz_offset)

        self.check_keep_current_orientation = QtWidgets.QCheckBox("Aktuelle TCP-Orientierung des Roboters beibehalten (empfohlen)")
        self.check_keep_current_orientation.setChecked(True)
        self.check_keep_current_orientation.setToolTip(
            "Sicherer Modus: X/Y/Z werden aus der Bildverarbeitung berechnet, "
            "RX/RY/RZ bleiben wie die aktuelle TCP-Orientierung. "
            "UR-Pose [rx,ry,rz] ist ein Rotationsvektor, kein Euler-RPY."
        )
        form2.addRow("Orientierung", self.check_keep_current_orientation)
        layout.addWidget(box_pose)

        self.check_enable_robot = QtWidgets.QCheckBox("Roboterbewegung aktivieren: Arbeitsraum ist frei, Not-Aus ist erreichbar")
        self.check_enable_robot.setStyleSheet("font-weight: bold; color: red;")
        layout.addWidget(self.check_enable_robot)

        row_pick = QtWidgets.QHBoxLayout()
        self.btn_preview_pose = QtWidgets.QPushButton("Aktuelle Zielpose berechnen")
        self.btn_move_approach = QtWidgets.QPushButton("Nur ueber Greifpunkt fahren")
        self.btn_pick = QtWidgets.QPushButton("Pick-Sequenz ausfuehren")
        self.btn_home = QtWidgets.QPushButton("Home anfahren")
        self.btn_home.setToolTip("Faehrt die eingestellte Home-Gelenkposition mit moveJ an.")
        self.btn_preview_pose.clicked.connect(self.preview_pose)
        self.btn_move_approach.clicked.connect(self.move_approach)
        self.btn_pick.clicked.connect(self.execute_pick_sequence)
        self.btn_home.clicked.connect(self.move_home)
        row_pick.addWidget(self.btn_preview_pose)
        row_pick.addWidget(self.btn_move_approach)
        row_pick.addWidget(self.btn_pick)
        row_pick.addWidget(self.btn_home)
        layout.addLayout(row_pick)

        self.status_robot = QtWidgets.QTextEdit()
        self.status_robot.setReadOnly(True)
        layout.addWidget(self.status_robot, stretch=1)

        self.tabs.addTab(tab, "3 UR3e + Robotiq")

    # ============================================================
    # RealSense und Updates
    # ============================================================

    def _start_realsense(self):
        self.pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.color, CAM_WIDTH, CAM_HEIGHT, rs.format.bgr8, CAM_FPS)
        self.pipeline.start(config)
        self.log_robot("RealSense gestartet.")

    def update_frame(self):
        if self.pipeline is None:
            return
        frames = self.pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        if not color_frame:
            return

        frame = np.asanyarray(color_frame.get_data())
        self.last_frame = frame

        x1 = max(0, ROI_X); y1 = max(0, ROI_Y)
        x2 = min(frame.shape[1], ROI_X + ROI_W); y2 = min(frame.shape[0], ROI_Y + ROI_H)
        roi = frame[y1:y2, x1:x2]
        self.last_roi = roi

        eval_img, mask, result = detect_triangle_in_roi(roi)
        self.last_eval = eval_img
        self.last_mask = mask
        self.last_result = result

        overview = frame.copy()
        cv2.rectangle(overview, (ROI_X, ROI_Y), (ROI_X + ROI_W, ROI_Y + ROI_H), (255, 0, 0), 2)
        if result is not None:
            gx_full = ROI_X + result.gx_roi
            gy_full = ROI_Y + result.gy_roi
            cv2.circle(overview, (gx_full, gy_full), 7, (0, 0, 255), -1)
            wx, wy = self.homography.pixel_to_world(gx_full, gy_full)
            cv2.putText(overview, f"X={wx:.1f} Y={wy:.1f} Yaw={result.yaw_ur3e_deg:.1f}",
                        (gx_full + 10, gy_full - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2, cv2.LINE_AA)

        self.lbl_overview.set_cv_image(overview)
        self.lbl_mask.set_cv_image(cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR))
        self.lbl_eval.set_cv_image(eval_img)

        # Homographie-Tab zeigt Gesamtbild mit bisher angeklickten Punkten
        h_img = overview.copy()
        for i, (u, v) in enumerate(self.homography.pixel_points):
            cv2.circle(h_img, (int(u), int(v)), 6, (0, 0, 255), -1)
            cv2.putText(h_img, str(i + 1), (int(u) + 7, int(v) - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        self.lbl_homography_img.set_cv_image(h_img)

        self.update_live_status()

    def update_live_status(self):
        if self.last_result is None:
            self.status_live.setPlainText("Status: Kein Objekt erkannt. ROI, HSV-Grenzen, Beleuchtung und MIN_AREA pruefen.")
            return
        r = self.last_result
        gx_full = ROI_X + r.gx_roi
        gy_full = ROI_Y + r.gy_roi
        cx_full = ROI_X + r.cx_roi
        cy_full = ROI_Y + r.cy_roi
        wx, wy = self.homography.pixel_to_world(gx_full, gy_full)
        h_status = "aktiv" if self.homography.is_valid() else "Fallback mm/Pixel"
        self.status_live.setPlainText(
            f"Status: Objekt erkannt | Homographie: {h_status}\n"
            f"Pixel: Schwerpunkt=({cx_full},{cy_full})  Greifpunkt=({gx_full},{gy_full})  Flaeche={r.area:.0f}px  Punkte={r.num_points}\n"
            f"Welt: X={wx:.1f} mm  Y={wy:.1f} mm  Kante={r.edge_angle_deg:.1f} deg  UR3e-Yaw={r.yaw_ur3e_deg:.1f} deg  Schliessrichtung={r.closing_direction_deg:.1f} deg"
        )

    # ============================================================
    # Homographie-Callbacks
    # ============================================================

    def get_current_tcp_xy_from_rtde_mm(self) -> Optional[tuple[float, float, float]]:
        """Liest die aktuelle TCP-Pose des UR-Roboters per UR_RTDE.

        Rueckgabe: (X_mm, Y_mm, Z_mm) im Roboter-Basiskoordinatensystem.
        UR_RTDE liefert Meter; fuer die Homographie verwenden wir Millimeter.
        """
        if rtde_receive is None:
            self.status_h.append("UR_RTDE nicht installiert: pip install ur_rtde")
            return None

        # Falls noch keine RTDE-Receive-Verbindung existiert, automatisch verbinden.
        if self.rtde_r is None:
            ip = self.edit_ur_ip.text().strip() if hasattr(self, "edit_ur_ip") else DEFAULT_UR_IP
            try:
                self.rtde_r = rtde_receive.RTDEReceiveInterface(ip)
                self.status_h.append(f"UR_RTDE Receive verbunden: {ip}")
                self.log_robot(f"UR_RTDE Receive verbunden: {ip}")
            except Exception as e:
                self.status_h.append(f"UR_RTDE Receive-Verbindung fehlgeschlagen: {e}")
                return None

        try:
            pose = self.rtde_r.getActualTCPPose()
            # pose = [x, y, z, rx, ry, rz] in m bzw. rad
            x_mm = float(pose[0]) * 1000.0
            y_mm = float(pose[1]) * 1000.0
            z_mm = float(pose[2]) * 1000.0
            return x_mm, y_mm, z_mm
        except Exception as e:
            self.status_h.append(f"TCP-Pose konnte nicht gelesen werden: {e}")
            return None

    def on_homography_image_clicked(self, u: int, v: int):
        if len(self.homography.pixel_points) >= 4:
            self.status_h.append("Bereits 4 Punkte vorhanden. Erst loeschen oder berechnen/speichern.")
            return

        tcp_xyz = self.get_current_tcp_xy_from_rtde_mm()
        if tcp_xyz is not None:
            world_x, world_y, world_z = tcp_xyz
            # Anzeige aktualisieren, damit die uebernommenen Werte sichtbar sind.
            self.spin_world_x.setValue(world_x)
            self.spin_world_y.setValue(world_y)
            source_text = f"UR_RTDE TCP: X={world_x:.1f} mm, Y={world_y:.1f} mm, Z={world_z:.1f} mm"
        else:
            # Fallback: manuell eingestellte Werte verwenden.
            world_x = float(self.spin_world_x.value())
            world_y = float(self.spin_world_y.value())
            source_text = "manuelle Weltkoordinaten aus den Eingabefeldern"

        self.homography.pixel_points.append((float(u), float(v)))
        self.homography.world_points.append((float(world_x), float(world_y)))
        self.refresh_homography_table()
        self.status_h.append(
            f"Punkt {len(self.homography.pixel_points)}: Pixel=({u},{v}) -> "
            f"Welt=({world_x:.1f},{world_y:.1f}) mm ({source_text})"
        )

    def refresh_homography_table(self):
        self.table_h.setRowCount(len(self.homography.pixel_points))
        for i, ((u, v), (x, y)) in enumerate(zip(self.homography.pixel_points, self.homography.world_points)):
            for col, val in enumerate([u, v, x, y]):
                self.table_h.setItem(i, col, QtWidgets.QTableWidgetItem(f"{val:.2f}"))

    def compute_homography(self):
        if self.homography.compute():
            self.status_h.append("Homographie berechnet. Pixel->Welt ist jetzt aktiv.")
            self.status_h.append(str(self.homography.H))
        else:
            self.status_h.append("Fehler: Mindestens 4 gueltige Pixel-/Welt-Punktpaare erforderlich.")

    def clear_homography(self):
        self.homography.clear()
        self.refresh_homography_table()
        self.status_h.setPlainText("Homographiepunkte geloescht.")

    def save_homography(self):
        if not self.homography.is_valid():
            self.status_h.append("Keine gueltige Homographie zum Speichern.")
            return
        self.homography.save(HOMOGRAPHY_FILE)
        self.status_h.append(f"Gespeichert: {HOMOGRAPHY_FILE}")

    def load_homography(self):
        if self.homography.load(HOMOGRAPHY_FILE):
            self.refresh_homography_table()
            self.status_h.append(f"Geladen: {HOMOGRAPHY_FILE}")
        else:
            self.status_h.append(f"Konnte {HOMOGRAPHY_FILE} nicht laden.")

    # ============================================================
    # Freedrive/Teach Mode
    # ============================================================

    def _set_freedrive_button_style(self, active: bool, blink_on: bool = True):
        """Optische Darstellung des Freedrive-Buttons."""
        if not hasattr(self, "btn_freedrive"):
            return
        if active:
            if blink_on:
                self.btn_freedrive.setStyleSheet(
                    "QPushButton { background-color: #ffd800; color: black; font-weight: bold; }"
                )
            else:
                self.btn_freedrive.setStyleSheet(
                    "QPushButton { background-color: #806c00; color: black; font-weight: bold; }"
                )
            self.btn_freedrive.setText("Freedrive AUS")
        else:
            self.btn_freedrive.setStyleSheet("")
            self.btn_freedrive.setText("Freedrive EIN")

    def _blink_freedrive_button(self):
        """Gelbes Blinken, solange Freedrive aktiv ist."""
        if not self.freedrive_enabled:
            self.freedrive_blink_timer.stop()
            self._set_freedrive_button_style(False)
            return
        self.freedrive_blink_on = not self.freedrive_blink_on
        self._set_freedrive_button_style(True, self.freedrive_blink_on)

    def toggle_freedrive(self):
        """Freedrive/Teach Mode am UR ein- oder ausschalten."""
        if self.rtde_c is None:
            self.status_h.append("Freedrive nicht moeglich: UR_RTDE ist nicht verbunden.")
            self.log_robot("Freedrive nicht moeglich: UR_RTDE ist nicht verbunden.")
            return

        try:
            if not self.freedrive_enabled:
                # ur_rtde nennt den Freedrive-Modus teachMode().
                self.rtde_c.teachMode()
                self.freedrive_enabled = True
                self.freedrive_blink_on = True
                self._set_freedrive_button_style(True, True)
                self.freedrive_blink_timer.start(500)
                self.status_h.append("Freedrive/Teach Mode EIN. Roboter von Hand fuehrbar.")
                self.log_robot("Freedrive/Teach Mode EIN.")
            else:
                self.rtde_c.endTeachMode()
                self.freedrive_enabled = False
                self.freedrive_blink_timer.stop()
                self._set_freedrive_button_style(False)
                self.status_h.append("Freedrive/Teach Mode AUS.")
                self.log_robot("Freedrive/Teach Mode AUS.")
        except Exception as e:
            self.freedrive_enabled = False
            self.freedrive_blink_timer.stop()
            self._set_freedrive_button_style(False)
            self.status_h.append(f"Freedrive-Fehler: {e}")
            self.log_robot(f"Freedrive-Fehler: {e}")

    # ============================================================
    # Robotik
    # ============================================================

    def log_robot(self, text: str):
        if hasattr(self, "status_robot"):
            self.status_robot.append(text)
        print(text)

    def connect_ur(self):
        if rtde_control is None or rtde_receive is None:
            self.log_robot("Fehler: ur_rtde nicht installiert. Installieren mit: pip install ur_rtde")
            return
        ip = self.edit_ur_ip.text().strip()
        try:
            self.rtde_c = rtde_control.RTDEControlInterface(ip)
            self.rtde_r = rtde_receive.RTDEReceiveInterface(ip)
            self.log_robot(f"UR_RTDE verbunden: {ip}")
        except Exception as e:
            self.log_robot(f"UR_RTDE Verbindungsfehler: {e}")

    def disconnect_ur(self):
        try:
            if self.rtde_c is not None:
                if self.freedrive_enabled:
                    try:
                        self.rtde_c.endTeachMode()
                    except Exception:
                        pass
                    self.freedrive_enabled = False
                    self.freedrive_blink_timer.stop()
                    self._set_freedrive_button_style(False)
                self.rtde_c.stopScript()
            self.rtde_c = None
            self.rtde_r = None
            self.log_robot("UR_RTDE getrennt.")
        except Exception as e:
            self.log_robot(f"Fehler beim Trennen: {e}")

    def connect_gripper(self):
        if RobotiqGripper is None:
            self.log_robot("Fehler: robotiq_gripper.py nicht gefunden oder Import fehlgeschlagen.")
            return
        ip = self.edit_gripper_ip.text().strip()
        port = int(self.spin_gripper_port.value())
        try:
            self.gripper = RobotiqGripper()
            self.gripper.connect(ip, port)
            self.gripper.activate(auto_calibrate=False)
            self.log_robot(f"Robotiq verbunden und aktiviert: {ip}:{port}")
        except Exception as e:
            self.gripper = None
            self.log_robot(f"Robotiq Fehler: {e}")

    def move_gripper(self, pos: int, speed: int = 64, force: int = 40):
        if self.gripper is None:
            self.log_robot("Gripper nicht verbunden.")
            return
        try:
            final_pos, obj = self.gripper.move_and_wait_for_pos(pos, speed, force)
            self.log_robot(f"Gripper pos={pos} -> final={final_pos}, object_status={obj}")
        except Exception as e:
            self.log_robot(f"Gripper-Bewegungsfehler: {e}")

    def get_actual_tcp_pose_safe(self) -> Optional[list[float]]:
        """Aktuelle TCP-Pose lesen. Rueckgabe: [x,y,z,rx,ry,rz] in m/rad.

        Wichtig: rx, ry, rz sind bei UR ein Rotationsvektor (Axis-Angle),
        nicht Roll/Pitch/Yaw-Eulerwinkel.
        """
        if self.rtde_r is None:
            self.log_robot("Keine RTDE-Receive-Verbindung: aktuelle TCP-Orientierung nicht verfuegbar.")
            return None
        try:
            pose = self.rtde_r.getActualTCPPose()
            if pose is None or len(pose) != 6:
                self.log_robot("Aktuelle TCP-Pose konnte nicht gelesen werden.")
                return None
            return [float(v) for v in pose]
        except Exception as e:
            self.log_robot(f"Fehler beim Lesen der aktuellen TCP-Pose: {e}")
            return None

    def current_target_pose(self) -> Optional[list[float]]:
        if self.last_result is None:
            self.log_robot("Keine Objektposition erkannt.")
            return None

        r = self.last_result
        gx_full = ROI_X + r.gx_roi
        gy_full = ROI_Y + r.gy_roi
        x_mm, y_mm = self.homography.pixel_to_world(gx_full, gy_full)

        x_m = x_mm / 1000.0
        y_m = y_mm / 1000.0
        z_m = float(self.spin_z.value())

        # WICHTIG:
        # UR-Pose [x,y,z,rx,ry,rz] benutzt fuer rx/ry/rz einen Rotationsvektor,
        # NICHT Eulerwinkel. Ein einfaches Setzen von rx=pi, ry=0, rz=yaw ist
        # deshalb oft kinematisch problematisch und kann zu Gelenkgrenzen fuehren.
        # Sicherer Standard: aktuelle TCP-Orientierung beibehalten.
        if hasattr(self, "check_keep_current_orientation") and self.check_keep_current_orientation.isChecked():
            actual_pose = self.get_actual_tcp_pose_safe()
            if actual_pose is None:
                return None
            rx, ry, rz = actual_pose[3], actual_pose[4], actual_pose[5]
        else:
            # Expertenmodus: feste Rotationsvektor-Komponenten verwenden.
            # Nicht als Roll/Pitch/Yaw interpretieren!
            yaw_rad = math.radians(r.yaw_ur3e_deg) + float(self.spin_rz_offset.value())
            rx, ry, rz = float(self.spin_rx.value()), float(self.spin_ry.value()), yaw_rad

        pose = [x_m, y_m, z_m, rx, ry, rz]
        return pose

    def validate_pose_with_ik(self, pose: list[float], name: str = "Zielpose") -> bool:
        """IK-Vorpruefung. Verhindert viele Fahrten in ungueltige Gelenkbereiche.
        Gibt False zurueck, wenn keine brauchbare IK-Loesung gefunden wird.
        """
        if self.rtde_c is None:
            self.log_robot("IK-Pruefung nicht moeglich: RTDE-Control nicht verbunden.")
            return False

        if any((not math.isfinite(v)) for v in pose):
            self.log_robot(f"{name} ungueltig: Pose enthaelt NaN/Inf: {pose}")
            return False

        # Grobe Plausibilitaet fuer UR3e-Arbeitsraum. Werte ggf. an Ihren Aufbau anpassen.
        x, y, z = pose[0], pose[1], pose[2]
        if not (-0.8 <= x <= 0.8 and -0.8 <= y <= 0.8 and 0.01 <= z <= 0.8):
            self.log_robot(
                f"WARNUNG {name}: x/y/z wirken ausserhalb des erwarteten UR3e-Arbeitsraums: "
                f"x={x:.3f}, y={y:.3f}, z={z:.3f} m"
            )

        qnear = []
        try:
            if self.rtde_r is not None:
                qnear = self.rtde_r.getActualQ()
        except Exception:
            qnear = []

        try:
            # ur_rtde unterstuetzt getInverseKinematics(pose, qnear, ...).
            # qnear bevorzugt eine IK-Loesung in der Naehe der aktuellen Gelenkstellung.
            q = self.rtde_c.getInverseKinematics(pose, qnear)
        except TypeError:
            try:
                q = self.rtde_c.getInverseKinematics(pose)
            except Exception as e:
                self.log_robot(f"IK-Fehler fuer {name}: {e}")
                return False
        except Exception as e:
            self.log_robot(f"IK-Fehler fuer {name}: {e}")
            return False

        if q is None or len(q) != 6:
            self.log_robot(f"Keine IK-Loesung fuer {name}. Fahrt wird nicht gestartet.")
            return False

        if any((not math.isfinite(float(v))) for v in q):
            self.log_robot(f"IK-Loesung ungueltig fuer {name}: {q}")
            return False

        self.log_robot(f"IK OK fuer {name}: " + ", ".join(f"{math.degrees(float(v)):.1f}°" for v in q))
        return True

    def lock_current_target_pose(self, purpose: str = "Zielpose") -> Optional[tuple[list[float], list[float]]]:
        """Berechnet die aktuelle Zielpose genau einmal und speichert sie.

        Wichtig fuer den Pick-Vorgang: Sobald der Roboter ueber das Objekt faehrt,
        kann der Greifer die Kamera verdecken. Deshalb darf die Zielpose nach dem
        Start nicht mehr aus dem Livebild aktualisiert werden.
        """
        pose = self.current_target_pose()
        if pose is None:
            return None
        approach = pose.copy()
        approach[2] += float(self.spin_approach.value())
        self.locked_target_pose = pose.copy()
        self.locked_approach_pose = approach.copy()
        self.log_robot(
            f"{purpose} eingefroren. Greifpose [x,y,z,rx,ry,rz]: "
            + ", ".join(f"{v:.4f}" for v in pose)
        )
        self.log_robot(
            "Anfahrpose eingefroren: " + ", ".join(f"{v:.4f}" for v in approach)
        )
        return pose, approach

    def parse_home_joints_rad(self) -> Optional[list[float]]:
        """Liest Home-Gelenkwinkel aus dem Eingabefeld und wandelt Grad -> rad."""
        try:
            parts = [p.strip().replace(";", ",") for p in self.edit_home_q.text().split(",")]
            vals_deg = [float(p) for p in parts if p != ""]
            if len(vals_deg) != 6:
                self.log_robot("Home q ungueltig: Bitte genau 6 Gelenkwinkel in Grad eingeben.")
                return None
            vals_rad = [math.radians(v) for v in vals_deg]
            if any(not math.isfinite(v) for v in vals_rad):
                self.log_robot("Home q ungueltig: NaN/Inf enthalten.")
                return None
            return vals_rad
        except Exception as e:
            self.log_robot(f"Home q konnte nicht gelesen werden: {e}")
            return None

    def move_home(self):
        """Faehrt den UR3e auf die eingestellte Home-Gelenkposition."""
        if not self.require_robot_enabled():
            return
        q_home = self.parse_home_joints_rad()
        if q_home is None:
            return
        try:
            speed = float(self.spin_home_speed.value())
            accel = float(self.spin_home_accel.value())
            self.log_robot(
                "Fahre Home q [deg]: " + ", ".join(f"{math.degrees(q):.1f}" for q in q_home)
            )
            self.rtde_c.moveJ(q_home, speed, accel)
            self.log_robot("Home-Position erreicht bzw. moveJ abgeschlossen.")
        except Exception as e:
            try:
                self.rtde_c.stopJ(1.0)
            except Exception:
                pass
            self.log_robot(f"Home-Fahrt Fehler: {e}")

    def preview_pose(self):
        pose = self.current_target_pose()
        if pose is None:
            return
        self.log_robot("Zielpose [x,y,z,rx,ry,rz]: " + ", ".join(f"{v:.4f}" for v in pose))
        self.validate_pose_with_ik(pose, "Vorschau-Zielpose")
        if not self.homography.is_valid():
            self.log_robot("WARNUNG: Keine Homographie aktiv. Pixel werden nur per Fallback-Skalierung in mm umgerechnet.")

    def require_robot_enabled(self) -> bool:
        if self.freedrive_enabled:
            self.log_robot("Roboterbewegung blockiert: Freedrive/Teach Mode ist noch aktiv.")
            return False
        if not self.check_enable_robot.isChecked():
            self.log_robot("Roboterbewegung blockiert: Sicherheitscheckbox ist nicht aktiviert.")
            return False
        if self.rtde_c is None:
            self.log_robot("UR_RTDE ist nicht verbunden.")
            return False
        return True

    def move_approach(self):
        if not self.require_robot_enabled():
            return
        locked = self.lock_current_target_pose("Fahrt ueber Greifpunkt")
        if locked is None:
            return
        pose, approach = locked
        if not self.validate_pose_with_ik(approach, "eingefrorene Anfahrpose"):
            return
        try:
            self.log_robot("Fahre eingefrorene Anfahrpose: " + ", ".join(f"{v:.4f}" for v in approach))
            self.rtde_c.moveL(approach, float(self.spin_speed.value()), float(self.spin_accel.value()))
        except Exception as e:
            try:
                self.rtde_c.stopL(1.0)
            except Exception:
                pass
            self.log_robot(f"moveL Fehler: {e}")

    def execute_pick_sequence(self):
        if not self.require_robot_enabled():
            return
        locked = self.lock_current_target_pose("Pick-Zielpose")
        if locked is None:
            return
        pose, approach = locked
        speed = float(self.spin_speed.value())
        accel = float(self.spin_accel.value())
        if not self.validate_pose_with_ik(approach, "eingefrorene Anfahrpose"):
            return
        if not self.validate_pose_with_ik(pose, "eingefrorene Greifpose"):
            return
        try:
            self.log_robot("Pick-Sequenz gestartet. Livebild wird fuer diese Bewegung nicht mehr als Zielquelle verwendet.")
            if self.gripper is not None:
                self.move_gripper(0, speed=80, force=20)
            self.rtde_c.moveL(approach, speed, accel)
            self.rtde_c.moveL(pose, speed, accel)
            if self.gripper is not None:
                self.move_gripper(180, speed=64, force=50)
            time.sleep(0.2)
            self.rtde_c.moveL(approach, speed, accel)
            self.log_robot("Pick-Sequenz beendet. Zielpose war waehrend der gesamten Sequenz eingefroren.")
        except Exception as e:
            try:
                self.rtde_c.stopL(1.0)
            except Exception:
                pass
            self.log_robot(f"Pick-Sequenz Fehler: {e}")

    def closeEvent(self, event):
        try:
            if self.pipeline is not None:
                self.pipeline.stop()
            if self.rtde_c is not None:
                if self.freedrive_enabled:
                    try:
                        self.rtde_c.endTeachMode()
                    except Exception:
                        pass
                self.rtde_c.stopScript()
            if self.gripper is not None:
                self.gripper.disconnect()
        except Exception:
            pass
        event.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
