"""
RealSense Dreieckserkennung + Homographie + UR3e/Robotiq Pick-Demo
===================================================================

Funktionen:
- RealSense D435/D435f RGB-Stream
- ROI-basierte HSV-Segmentierung eines gruenen Dreieckobjekts
- Konturvereinfachung mit approxPolyDP
- Greifpunkt und Greiferwinkel aus der laengsten Dreieckskante
- optionale Homographie Pixel -> Weltkoordinaten
- UR3e-Ansteuerung ueber ur_rtde
- Robotiq 2F-Gripper ueber robotiq_gripper.py
- Freedrive/Teach-Mode fuer Homographie-Einlernen
- Pick-Sequenz als Zustandsautomat
- Zielpose wird beim Pick-Start eingefroren, damit Kameraabschattung keine Rolle spielt

Sicherheit:
- Roboterbewegung ist nur nach Aktivierung der Sicherheitscheckbox moeglich.
- Vor jeder Fahrt wird eine IK-Vorpruefung durchgefuehrt.
- Testen Sie zuerst mit niedriger Geschwindigkeit und grossem Abstand.

Hinweis UR-Pose:
UR-Pose [x, y, z, rx, ry, rz] verwendet fuer rx/ry/rz einen Rotationsvektor
(Axis-Angle), nicht Euler-Roll/Pitch/Yaw.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import pyrealsense2 as rs
from PyQt6 import QtCore, QtGui, QtWidgets

# -----------------------------------------------------------------------------
# Optional: Projektverzeichnis in den Python-Suchpfad aufnehmen
# Dadurch wird robotiq_gripper.py auch gefunden, wenn dieses Skript im Unterordner
# openCV liegt und robotiq_gripper.py eine Ebene darueber.
# -----------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))
if str(PROJECT_DIR) not in sys.path:
    sys.path.append(str(PROJECT_DIR))

try:
    import rtde_control
    import rtde_receive
except Exception:  # ur_rtde ist optional, damit die Bildverarbeitung auch ohne Roboter laeuft
    rtde_control = None
    rtde_receive = None

try:
    from robotiq_gripper import RobotiqGripper
except Exception:
    RobotiqGripper = None


# =============================================================================
# Konfiguration
# =============================================================================

@dataclass(frozen=True)
class CameraConfig:
    width: int = 640
    height: int = 480
    fps: int = 6


@dataclass(frozen=True)
class RoiConfig:
    x: int = 260
    y: int = 120
    w: int = 260
    h: int = 220


@dataclass(frozen=True)
class VisionConfig:
    hsv_lower: np.ndarray = field(default_factory=lambda: np.array([38, 80, 50], dtype=np.uint8))
    hsv_upper: np.ndarray = field(default_factory=lambda: np.array([60, 255, 220], dtype=np.uint8))
    min_area: float = 300.0
    approx_eps_factor: float = 0.04
    grasp_shift_factor: float = 0.15
    angle_filter_alpha: float = 0.20
    camera_to_robot_yaw_offset_deg: float = 0.0


@dataclass(frozen=True)
class WorldConfig:
    mm_per_pixel_x: float = 1.0
    mm_per_pixel_y: float = 1.0
    x_offset_mm: float = 0.0
    y_offset_mm: float = 0.0
    axis_origin_mm: tuple[float, float] = (0.0, 0.0)
    axis_length_mm: float = 100.0
    homography_file: str = "homography_triangle_ur3e.json"


@dataclass(frozen=True)
class RobotConfig:
    default_ur_ip: str = "192.168.0.17"
    default_gripper_ip: str = "192.168.0.17"
    default_gripper_port: int = 63352

    tcp_z_m: float = -0.020  # Greifhoehe. Urspruenglich 0.090, spaeter 11 cm tiefer.
    approach_m: float = 0.060
    speed_m_s: float = 0.04
    accel_m_s2: float = 0.05

    # Nur im Expertenmodus verwendet. UR nutzt Rotationsvektor, nicht Euler-RPY.
    rx_default: float = math.pi
    ry_default: float = 0.0
    rz_offset_default: float = 0.0

    home_q_deg: tuple[float, float, float, float, float, float] = (0.0, -90.0, 90.0, -90.0, -90.0, 0.0)
    home_speed_rad_s: float = 0.30
    home_accel_rad_s2: float = 0.20

    # Grobe Plausibilitaetsgrenzen fuer UR3e. An Laboraufbau anpassen.
    x_min_m: float = -0.8
    x_max_m: float = 0.8
    y_min_m: float = -0.8
    y_max_m: float = 0.8
    z_min_m: float = -0.20
    z_max_m: float = 0.8


@dataclass(frozen=True)
class DrawConfig:
    gripper_axis_half_length_px: int = 55
    gripper_finger_length_px: int = 35
    gripper_finger_offset_px: int = 30


CAMERA = CameraConfig()
ROI = RoiConfig()
VISION = VisionConfig()
WORLD = WorldConfig()
ROBOT = RobotConfig()
DRAW = DrawConfig()


# =============================================================================
# Datenstrukturen
# =============================================================================

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


class PickState(Enum):
    IDLE = auto()
    LOCK_TARGET = auto()
    OPEN_GRIPPER = auto()
    MOVE_PREGRASP = auto()
    MOVE_GRASP = auto()
    CLOSE_GRIPPER = auto()
    LIFT_OBJECT = auto()
    FINISHED = auto()
    ERROR = auto()


# =============================================================================
# Hilfsfunktionen: Winkel, Anzeige
# =============================================================================

def normalize_angle_180(angle_deg: float) -> float:
    """Normiert einen Linienwinkel auf [0, 180)."""
    return angle_deg % 180.0


def normalize_angle_360(angle_deg: float) -> float:
    """Normiert einen Richtungswinkel auf [0, 360)."""
    return angle_deg % 360.0


class AngleLowPass180:
    """Exponentieller Tiefpass fuer Winkel mit 180-Grad-Periodizitaet.

    0 Grad und 180 Grad beschreiben bei einer Kante dieselbe Linie. Deshalb wird
    die Winkeldifferenz vor dem Filtern auf [-90, 90] gebracht.
    """

    def __init__(self, alpha: float):
        self.alpha = float(alpha)
        self.value: Optional[float] = None

    def reset(self) -> None:
        self.value = None

    def update(self, angle_deg: float) -> float:
        angle_deg = normalize_angle_180(angle_deg)
        if self.value is None:
            self.value = angle_deg
            return self.value

        diff = angle_deg - self.value
        while diff > 90.0:
            diff -= 180.0
        while diff < -90.0:
            diff += 180.0

        self.value = normalize_angle_180(self.value + self.alpha * diff)
        return self.value


def bgr_to_qpixmap(img_bgr: np.ndarray) -> QtGui.QPixmap:
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    qimg = QtGui.QImage(rgb.data, w, h, ch * w, QtGui.QImage.Format.Format_RGB888)
    return QtGui.QPixmap.fromImage(qimg.copy())


def draw_text(img: np.ndarray, text: str, pos: tuple[int, int], scale: float = 0.55,
              color: tuple[int, int, int] = (255, 255, 255), thickness: int = 1) -> None:
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


# =============================================================================
# Bildverarbeitung
# =============================================================================

class TriangleDetector:
    def __init__(self, config: VisionConfig):
        self.config = config
        self.angle_filter = AngleLowPass180(config.angle_filter_alpha)

    def create_mask(self, img_bgr: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.config.hsv_lower, self.config.hsv_upper)
        kernel = np.ones((7, 7), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        return mask

    @staticmethod
    def longest_edge(points: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
        edges: list[tuple[float, np.ndarray, np.ndarray]] = []
        n = len(points)
        for i in range(n):
            p1 = points[i]
            p2 = points[(i + 1) % n]
            length = float(np.linalg.norm(p2 - p1))
            edges.append((length, p1, p2))
        return max(edges, key=lambda e: e[0])

    def detect(self, roi_bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray, Optional[DetectionResult]]:
        mask = self.create_mask(roi_bgr)
        eval_img = roi_bgr.copy()

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return eval_img, mask, None

        cnt = max(contours, key=cv2.contourArea)
        area = float(cv2.contourArea(cnt))
        if area < self.config.min_area:
            return eval_img, mask, None

        moments = cv2.moments(cnt)
        if moments["m00"] == 0:
            return eval_img, mask, None

        cx = int(moments["m10"] / moments["m00"])
        cy = int(moments["m01"] / moments["m00"])

        epsilon = self.config.approx_eps_factor * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        points = approx.reshape(-1, 2)
        if len(points) < 3:
            return eval_img, mask, None

        _, p1, p2 = self.longest_edge(points)
        dx = float(p2[0] - p1[0])
        dy = float(p2[1] - p1[1])

        edge_raw = normalize_angle_180(math.degrees(math.atan2(dy, dx)))
        edge_filtered = self.angle_filter.update(edge_raw)
        closing_dir = normalize_angle_180(edge_filtered + 90.0)
        yaw_ur3e = normalize_angle_180(edge_filtered + self.config.camera_to_robot_yaw_offset_deg)

        edge_mid = (p1.astype(float) + p2.astype(float)) / 2.0
        center = np.array([cx, cy], dtype=float)
        grasp = center + self.config.grasp_shift_factor * (edge_mid - center)
        gx, gy = int(round(grasp[0])), int(round(grasp[1]))

        self._draw_detection(eval_img, cnt, points, p1, p2, cx, cy, gx, gy, edge_filtered, yaw_ur3e, closing_dir)

        return eval_img, mask, DetectionResult(
            cx_roi=cx,
            cy_roi=cy,
            gx_roi=gx,
            gy_roi=gy,
            edge_angle_deg=edge_filtered,
            edge_angle_raw_deg=edge_raw,
            closing_direction_deg=closing_dir,
            yaw_ur3e_deg=yaw_ur3e,
            area=area,
            num_points=len(points),
        )

    @staticmethod
    def _draw_detection(eval_img: np.ndarray, cnt: np.ndarray, points: np.ndarray,
                        p1: np.ndarray, p2: np.ndarray, cx: int, cy: int,
                        gx: int, gy: int, edge_deg: float, yaw_deg: float,
                        closing_deg: float) -> None:
        cv2.drawContours(eval_img, [cnt], -1, (0, 255, 0), 2)
        cv2.polylines(eval_img, [points.astype(np.int32)], True, (255, 0, 255), 2)
        cv2.line(eval_img, tuple(p1), tuple(p2), (255, 255, 0), 4)
        cv2.circle(eval_img, (cx, cy), 6, (255, 0, 0), -1)  # Schwerpunkt
        cv2.circle(eval_img, (gx, gy), 6, (0, 0, 255), -1)   # Greifpunkt

        # Schliessrichtung
        length = 70
        a = math.radians(closing_deg)
        x2 = int(gx + length * math.cos(a))
        y2 = int(gy + length * math.sin(a))
        cv2.arrowedLine(eval_img, (gx, gy), (x2, y2), (0, 255, 255), 3, tipLength=0.25)

        draw_text(eval_img, f"Kante: {edge_deg:.1f} deg", (10, 28), 0.60, (0, 0, 255), 2)
        draw_text(eval_img, f"UR3e Yaw: {yaw_deg:.1f} deg", (10, 55), 0.60, (0, 0, 255), 2)


def draw_gripper_symbol(img: np.ndarray, center: tuple[int, int], edge_angle_deg: float,
                        label: str = "Greifer") -> None:
    """Zeichnet eine schematische Draufsicht des Robotiq-2F-Greifers.

    Standardstrategie in diesem Skript:
    - Greiferachse parallel zur laengsten Kante
    - Schliessrichtung senkrecht zur laengsten Kante
    """
    cx, cy = int(center[0]), int(center[1])
    a = math.radians(edge_angle_deg)
    axis = np.array([math.cos(a), math.sin(a)], dtype=float)
    close = np.array([-math.sin(a), math.cos(a)], dtype=float)

    center_vec = np.array([cx, cy], dtype=float)
    left = center_vec - DRAW.gripper_axis_half_length_px * axis
    right = center_vec + DRAW.gripper_axis_half_length_px * axis
    cv2.line(img, tuple(np.round(left).astype(int)), tuple(np.round(right).astype(int)), (0, 255, 255), 2)

    for sign in (-1, 1):
        base = center_vec + sign * DRAW.gripper_finger_offset_px * axis
        f1 = base - 0.5 * DRAW.gripper_finger_length_px * close
        f2 = base + 0.5 * DRAW.gripper_finger_length_px * close
        cv2.line(img, tuple(np.round(f1).astype(int)), tuple(np.round(f2).astype(int)), (0, 200, 255), 4)

    # Doppelpfeil Schliessrichtung
    p1 = center_vec - 35 * close
    p2 = center_vec + 35 * close
    cv2.arrowedLine(img, tuple(np.round(p1).astype(int)), tuple(np.round(p2).astype(int)), (0, 255, 0), 2, tipLength=0.25)
    cv2.arrowedLine(img, tuple(np.round(p2).astype(int)), tuple(np.round(p1).astype(int)), (0, 255, 0), 2, tipLength=0.25)

    cv2.circle(img, (cx, cy), 5, (0, 0, 255), -1)
    draw_text(img, label, (cx + 10, cy + 20), 0.50, (0, 255, 255), 1)


# =============================================================================
# Homographie
# =============================================================================

class HomographyModel:
    def __init__(self, world_cfg: WorldConfig):
        self.world_cfg = world_cfg
        self.pixel_points: list[tuple[float, float]] = []
        self.world_points: list[tuple[float, float]] = []
        self.H: Optional[np.ndarray] = None

    def clear(self) -> None:
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
            return (
                self.world_cfg.x_offset_mm + u * self.world_cfg.mm_per_pixel_x,
                self.world_cfg.y_offset_mm + v * self.world_cfg.mm_per_pixel_y,
            )

        p = np.array([[[float(u), float(v)]]], dtype=np.float32)
        w = cv2.perspectiveTransform(p, self.H)[0, 0]
        return float(w[0]), float(w[1])

    def world_to_pixel(self, x_mm: float, y_mm: float) -> Optional[tuple[int, int]]:
        if self.H is None:
            return None
        try:
            H_inv = np.linalg.inv(self.H)
            p = np.array([[[float(x_mm), float(y_mm)]]], dtype=np.float32)
            uv = cv2.perspectiveTransform(p, H_inv)[0, 0]
            return int(round(float(uv[0]))), int(round(float(uv[1])))
        except Exception:
            return None

    def save(self, path: str | os.PathLike[str]) -> None:
        data = {
            "pixel_points": self.pixel_points,
            "world_points": self.world_points,
            "H": self.H.tolist() if self.H is not None else None,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str | os.PathLike[str]) -> bool:
        if not os.path.exists(path):
            return False
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.pixel_points = [tuple(p) for p in data.get("pixel_points", [])]
        self.world_points = [tuple(p) for p in data.get("world_points", [])]
        H = data.get("H")
        self.H = np.array(H, dtype=np.float64) if H is not None else None
        return self.H is not None


def draw_world_coordinate_system(img: np.ndarray, homography: HomographyModel) -> None:
    if not homography.is_valid():
        draw_text(img, "Welt-KS: keine Homographie", (12, img.shape[0] - 18), 0.55, (0, 0, 255), 2)
        return

    ox_mm, oy_mm = WORLD.axis_origin_mm
    origin = homography.world_to_pixel(ox_mm, oy_mm)
    x_end = homography.world_to_pixel(ox_mm + WORLD.axis_length_mm, oy_mm)
    y_end = homography.world_to_pixel(ox_mm, oy_mm + WORLD.axis_length_mm)
    if origin is None or x_end is None or y_end is None:
        return

    cv2.circle(img, origin, 6, (255, 255, 255), -1)
    cv2.arrowedLine(img, origin, x_end, (0, 0, 255), 3, tipLength=0.18)
    cv2.arrowedLine(img, origin, y_end, (0, 255, 0), 3, tipLength=0.18)
    draw_text(img, "X", (x_end[0] + 6, x_end[1]), 0.75, (0, 0, 255), 2)
    draw_text(img, "Y", (y_end[0] + 6, y_end[1]), 0.75, (0, 255, 0), 2)
    draw_text(img, "Welt-KS", (origin[0] + 8, origin[1] - 8), 0.55, (255, 255, 255), 2)


# =============================================================================
# Roboter-Wrapper
# =============================================================================

class RobotInterface:
    def __init__(self, log_callback):
        self.log = log_callback
        self.rtde_c = None
        self.rtde_r = None
        self.gripper = None
        self.freedrive_enabled = False

    def connect_ur(self, ip: str) -> bool:
        if rtde_control is None or rtde_receive is None:
            self.log("Fehler: ur_rtde nicht installiert. Installieren mit: pip install ur_rtde")
            return False
        try:
            self.rtde_c = rtde_control.RTDEControlInterface(ip)
            self.rtde_r = rtde_receive.RTDEReceiveInterface(ip)
            self.log(f"UR_RTDE verbunden: {ip}")
            return True
        except Exception as e:
            self.rtde_c = None
            self.rtde_r = None
            self.log(f"UR_RTDE Verbindungsfehler: {e}")
            return False

    def disconnect_ur(self) -> None:
        try:
            if self.rtde_c is not None:
                if self.freedrive_enabled:
                    try:
                        self.rtde_c.endTeachMode()
                    except Exception:
                        pass
                    self.freedrive_enabled = False
                self.rtde_c.stopScript()
            self.rtde_c = None
            self.rtde_r = None
            self.log("UR_RTDE getrennt.")
        except Exception as e:
            self.log(f"Fehler beim Trennen: {e}")

    def ensure_receive_connection(self, ip: str) -> bool:
        if rtde_receive is None:
            self.log("UR_RTDE Receive nicht installiert: pip install ur_rtde")
            return False
        if self.rtde_r is not None:
            return True
        try:
            self.rtde_r = rtde_receive.RTDEReceiveInterface(ip)
            self.log(f"UR_RTDE Receive verbunden: {ip}")
            return True
        except Exception as e:
            self.log(f"UR_RTDE Receive-Verbindung fehlgeschlagen: {e}")
            return False

    def get_actual_tcp_pose(self) -> Optional[list[float]]:
        if self.rtde_r is None:
            self.log("Keine RTDE-Receive-Verbindung: TCP-Pose nicht verfuegbar.")
            return None
        try:
            pose = self.rtde_r.getActualTCPPose()
            if pose is None or len(pose) != 6:
                self.log("Aktuelle TCP-Pose konnte nicht gelesen werden.")
                return None
            return [float(v) for v in pose]
        except Exception as e:
            self.log(f"Fehler beim Lesen der TCP-Pose: {e}")
            return None

    def get_actual_tcp_xyz_mm(self) -> Optional[tuple[float, float, float]]:
        pose = self.get_actual_tcp_pose()
        if pose is None:
            return None
        return pose[0] * 1000.0, pose[1] * 1000.0, pose[2] * 1000.0

    def get_actual_q(self) -> list[float]:
        if self.rtde_r is None:
            return []
        try:
            return list(self.rtde_r.getActualQ())
        except Exception:
            return []

    def validate_pose_with_ik(self, pose: list[float], name: str) -> bool:
        if self.rtde_c is None:
            self.log("IK-Pruefung nicht moeglich: RTDE-Control nicht verbunden.")
            return False
        if any(not math.isfinite(v) for v in pose):
            self.log(f"{name} ungueltig: Pose enthaelt NaN/Inf: {pose}")
            return False

        x, y, z = pose[:3]
        if not (ROBOT.x_min_m <= x <= ROBOT.x_max_m and
                ROBOT.y_min_m <= y <= ROBOT.y_max_m and
                ROBOT.z_min_m <= z <= ROBOT.z_max_m):
            self.log(
                f"WARNUNG {name}: x/y/z ausserhalb des erwarteten Bereichs: "
                f"x={x:.3f}, y={y:.3f}, z={z:.3f} m"
            )

        qnear = self.get_actual_q()
        try:
            q = self.rtde_c.getInverseKinematics(pose, qnear)
        except TypeError:
            try:
                q = self.rtde_c.getInverseKinematics(pose)
            except Exception as e:
                self.log(f"IK-Fehler fuer {name}: {e}")
                return False
        except Exception as e:
            self.log(f"IK-Fehler fuer {name}: {e}")
            return False

        if q is None or len(q) != 6 or any(not math.isfinite(float(v)) for v in q):
            self.log(f"Keine gueltige IK-Loesung fuer {name}. Fahrt wird nicht gestartet.")
            return False

        self.log("IK OK fuer " + name + ": " + ", ".join(f"{math.degrees(float(v)):.1f}°" for v in q))
        return True

    def move_l(self, pose: list[float], speed: float, accel: float, name: str) -> bool:
        if self.rtde_c is None:
            self.log("moveL nicht moeglich: RTDE-Control nicht verbunden.")
            return False
        if not self.validate_pose_with_ik(pose, name):
            return False
        try:
            self.log(f"moveL {name}: " + ", ".join(f"{v:.4f}" for v in pose))
            self.rtde_c.moveL(pose, speed, accel)
            return True
        except Exception as e:
            try:
                self.rtde_c.stopL(1.0)
            except Exception:
                pass
            self.log(f"moveL Fehler ({name}): {e}")
            return False

    def move_j(self, q_rad: list[float], speed: float, accel: float, name: str) -> bool:
        if self.rtde_c is None:
            self.log("moveJ nicht moeglich: RTDE-Control nicht verbunden.")
            return False
        try:
            self.log(f"moveJ {name}: " + ", ".join(f"{math.degrees(q):.1f}°" for q in q_rad))
            self.rtde_c.moveJ(q_rad, speed, accel)
            return True
        except Exception as e:
            try:
                self.rtde_c.stopJ(1.0)
            except Exception:
                pass
            self.log(f"moveJ Fehler ({name}): {e}")
            return False

    def stop_motion(self) -> None:
        if self.rtde_c is None:
            return
        try:
            self.rtde_c.stopL(1.0)
        except Exception:
            pass
        try:
            self.rtde_c.stopJ(1.0)
        except Exception:
            pass

    def set_freedrive(self, enabled: bool) -> bool:
        if self.rtde_c is None:
            self.log("Freedrive nicht moeglich: UR_RTDE ist nicht verbunden.")
            return False
        try:
            if enabled:
                self.rtde_c.teachMode()
                self.freedrive_enabled = True
                self.log("Freedrive/Teach Mode EIN.")
            else:
                self.rtde_c.endTeachMode()
                self.freedrive_enabled = False
                self.log("Freedrive/Teach Mode AUS.")
            return True
        except Exception as e:
            self.freedrive_enabled = False
            self.log(f"Freedrive-Fehler: {e}")
            return False

    def connect_gripper(self, ip: str, port: int) -> bool:
        if RobotiqGripper is None:
            self.log("Fehler: robotiq_gripper.py nicht gefunden oder Import fehlgeschlagen.")
            return False
        try:
            self.gripper = RobotiqGripper()
            self.gripper.connect(ip, port)
            self.gripper.activate(auto_calibrate=False)
            self.log(f"Robotiq verbunden und aktiviert: {ip}:{port}")
            return True
        except Exception as e:
            self.gripper = None
            self.log(f"Robotiq Fehler: {e}")
            return False

    def move_gripper(self, pos: int, speed: int = 64, force: int = 40) -> bool:
        if self.gripper is None:
            self.log("Gripper nicht verbunden.")
            return False
        try:
            final_pos, obj = self.gripper.move_and_wait_for_pos(pos, speed, force)
            self.log(f"Gripper pos={pos} -> final={final_pos}, object_status={obj}")
            return True
        except Exception as e:
            self.log(f"Gripper-Bewegungsfehler: {e}")
            return False

    def disconnect_gripper(self) -> None:
        if self.gripper is None:
            return
        try:
            self.gripper.disconnect()
        except Exception:
            pass
        self.gripper = None


# =============================================================================
# GUI-Elemente
# =============================================================================

class ImageLabel(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal(int, int)

    def __init__(self, title: str = ""):
        super().__init__()
        self.title = title
        self.setMinimumSize(320, 240)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: black; color: white;")
        self._last_pixmap_size: Optional[tuple[int, int]] = None
        self._source_size: Optional[tuple[int, int]] = None

    def set_cv_image(self, img_bgr: np.ndarray) -> None:
        self._source_size = (img_bgr.shape[1], img_bgr.shape[0])
        pix = bgr_to_qpixmap(img_bgr)
        scaled = pix.scaled(
            self.size(),
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
        self._last_pixmap_size = (scaled.width(), scaled.height())
        self.setPixmap(scaled)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
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


# =============================================================================
# Hauptfenster
# =============================================================================

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RealSense Dreieckserkennung + Homographie + UR3e/Robotiq")
        self.resize(1300, 850)

        self.detector = TriangleDetector(VISION)
        self.homography = HomographyModel(WORLD)
        self.homography.load(WORLD.homography_file)
        self.robot = RobotInterface(self.log_robot)

        self.pipeline: Optional[rs.pipeline] = None
        self.last_frame: Optional[np.ndarray] = None
        self.last_roi: Optional[np.ndarray] = None
        self.last_eval: Optional[np.ndarray] = None
        self.last_mask: Optional[np.ndarray] = None
        self.last_result: Optional[DetectionResult] = None

        self.locked_target_pose: Optional[list[float]] = None
        self.locked_approach_pose: Optional[list[float]] = None
        self.pick_state = PickState.IDLE
        self.pick_state_busy = False

        self.freedrive_blink_on = False
        self.freedrive_blink_timer = QtCore.QTimer(self)
        self.freedrive_blink_timer.timeout.connect(self._blink_freedrive_button)

        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)
        self._build_live_tab()
        self._build_homography_tab()
        self._build_robot_tab()

        self._start_realsense()

        self.camera_timer = QtCore.QTimer(self)
        self.camera_timer.timeout.connect(self.update_frame)
        self.camera_timer.start(30)

        self.pick_timer = QtCore.QTimer(self)
        self.pick_timer.timeout.connect(self.run_pick_state_machine)
        self.pick_timer.start(50)

    # ------------------------------------------------------------------
    # GUI-Aufbau
    # ------------------------------------------------------------------
    def _build_live_tab(self) -> None:
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

    def _build_homography_tab(self) -> None:
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
        self.btn_freedrive = QtWidgets.QPushButton("Freedrive EIN")
        self.btn_freedrive.setToolTip("UR3e in den Freedrive/Teach Mode setzen. Erneut klicken zum Beenden.")

        self.btn_h_compute.clicked.connect(self.compute_homography)
        self.btn_h_clear.clicked.connect(self.clear_homography)
        self.btn_h_save.clicked.connect(self.save_homography)
        self.btn_h_load.clicked.connect(self.load_homography)
        self.btn_freedrive.clicked.connect(self.toggle_freedrive)

        btns.addWidget(self.btn_h_compute, 0, 0)
        btns.addWidget(self.btn_h_clear, 0, 1)
        btns.addWidget(self.btn_h_save, 1, 0)
        btns.addWidget(self.btn_h_load, 1, 1)
        btns.addWidget(self.btn_freedrive, 2, 0, 1, 2)
        right.addLayout(btns)

        self.status_h = QtWidgets.QTextEdit()
        self.status_h.setReadOnly(True)
        self.status_h.setPlainText("Homographie geladen." if self.homography.is_valid() else "Homographie: Noch nicht berechnet/geladen.")
        right.addWidget(self.status_h)

        main.addLayout(right, stretch=1)
        self.tabs.addTab(tab, "2 Homographie")

    def _build_robot_tab(self) -> None:
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        # Verbindung
        box_conn = QtWidgets.QGroupBox("Verbindung")
        form = QtWidgets.QFormLayout(box_conn)
        self.edit_ur_ip = QtWidgets.QLineEdit(ROBOT.default_ur_ip)
        self.edit_gripper_ip = QtWidgets.QLineEdit(ROBOT.default_gripper_ip)
        self.spin_gripper_port = QtWidgets.QSpinBox()
        self.spin_gripper_port.setRange(1, 65535)
        self.spin_gripper_port.setValue(ROBOT.default_gripper_port)
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
        self.btn_gripper_open.clicked.connect(lambda: self.robot.move_gripper(0, speed=64, force=30))
        self.btn_gripper_close.clicked.connect(lambda: self.robot.move_gripper(180, speed=64, force=50))

        for button in (self.btn_connect_ur, self.btn_disconnect_ur, self.btn_connect_gripper,
                       self.btn_gripper_open, self.btn_gripper_close):
            row_conn.addWidget(button)
        layout.addLayout(row_conn)

        # Pose/Sicherheit
        box_pose = QtWidgets.QGroupBox("Greifpose / Sicherheitsparameter")
        form2 = QtWidgets.QFormLayout(box_pose)

        self.spin_z = self._make_double_spin(-1.0, 1.5, 4, 0.005, ROBOT.tcp_z_m, " m")
        self.spin_approach = self._make_double_spin(0.0, 0.5, 4, 0.005, ROBOT.approach_m, " m")
        self.spin_speed = self._make_double_spin(0.001, 0.5, 3, 0.001, ROBOT.speed_m_s, " m/s")
        self.spin_accel = self._make_double_spin(0.001, 1.0, 3, 0.001, ROBOT.accel_m_s2, " m/s²")
        self.spin_rx = self._make_double_spin(-math.pi, math.pi, 4, 0.01, ROBOT.rx_default, "")
        self.spin_ry = self._make_double_spin(-math.pi, math.pi, 4, 0.01, ROBOT.ry_default, "")
        self.spin_rz_offset = self._make_double_spin(-math.pi, math.pi, 4, 0.01, ROBOT.rz_offset_default, "")

        form2.addRow("Greif-Z TCP", self.spin_z)
        form2.addRow("Anfahrhoehe ueber Greif-Z", self.spin_approach)
        form2.addRow("Geschwindigkeit", self.spin_speed)
        form2.addRow("Beschleunigung", self.spin_accel)

        self.edit_home_q = QtWidgets.QLineEdit(", ".join(f"{v:.1f}" for v in ROBOT.home_q_deg))
        self.edit_home_q.setToolTip("Home-Gelenkwinkel in Grad: q0, q1, q2, q3, q4, q5")
        self.spin_home_speed = self._make_double_spin(0.01, 1.0, 2, 0.01, ROBOT.home_speed_rad_s, " rad/s")
        self.spin_home_accel = self._make_double_spin(0.01, 2.0, 2, 0.01, ROBOT.home_accel_rad_s2, " rad/s²")
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

        self.lbl_pick_state = QtWidgets.QLabel("Pick-Zustand: IDLE")
        self.lbl_pick_state.setStyleSheet("font-weight: bold; padding: 6px; background-color: #e8e8e8;")
        layout.addWidget(self.lbl_pick_state)

        row_pick = QtWidgets.QHBoxLayout()
        self.btn_preview_pose = QtWidgets.QPushButton("Aktuelle Zielpose berechnen")
        self.btn_move_approach = QtWidgets.QPushButton("Nur ueber Greifpunkt fahren")
        self.btn_pick = QtWidgets.QPushButton("Pick-Sequenz ausfuehren")
        self.btn_abort_pick = QtWidgets.QPushButton("Pick stoppen")
        self.btn_home = QtWidgets.QPushButton("Home anfahren")

        self.btn_preview_pose.clicked.connect(self.preview_pose)
        self.btn_move_approach.clicked.connect(self.move_approach)
        self.btn_pick.clicked.connect(self.execute_pick_sequence)
        self.btn_abort_pick.clicked.connect(self.abort_pick_sequence)
        self.btn_home.clicked.connect(self.move_home)

        for button in (self.btn_preview_pose, self.btn_move_approach, self.btn_pick,
                       self.btn_abort_pick, self.btn_home):
            row_pick.addWidget(button)
        layout.addLayout(row_pick)

        self.status_robot = QtWidgets.QTextEdit()
        self.status_robot.setReadOnly(True)
        layout.addWidget(self.status_robot, stretch=1)

        self.tabs.addTab(tab, "3 UR3e + Robotiq")

    @staticmethod
    def _make_double_spin(minimum: float, maximum: float, decimals: int, step: float,
                          value: float, suffix: str) -> QtWidgets.QDoubleSpinBox:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(decimals)
        spin.setSingleStep(step)
        spin.setValue(value)
        spin.setSuffix(suffix)
        return spin

    # ------------------------------------------------------------------
    # RealSense/Livebild
    # ------------------------------------------------------------------
    def _start_realsense(self) -> None:
        self.pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.color, CAMERA.width, CAMERA.height, rs.format.bgr8, CAMERA.fps)
        self.pipeline.start(config)
        self.log_robot("RealSense gestartet.")

    def update_frame(self) -> None:
        if self.pipeline is None:
            return
        try:
            frames = self.pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            if not color_frame:
                return
            frame = np.asanyarray(color_frame.get_data())
        except Exception as e:
            self.log_robot(f"RealSense Fehler: {e}")
            return

        self.last_frame = frame
        roi = self._extract_roi(frame)
        self.last_roi = roi

        eval_img, mask, result = self.detector.detect(roi)
        self.last_eval = eval_img
        self.last_mask = mask
        self.last_result = result

        overview = self._create_overview_image(frame, result)
        homography_img = self._create_homography_image(overview)

        self.lbl_overview.set_cv_image(overview)
        self.lbl_mask.set_cv_image(cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR))
        self.lbl_eval.set_cv_image(eval_img)
        self.lbl_homography_img.set_cv_image(homography_img)
        self.update_live_status()

    @staticmethod
    def _extract_roi(frame: np.ndarray) -> np.ndarray:
        x1 = max(0, ROI.x)
        y1 = max(0, ROI.y)
        x2 = min(frame.shape[1], ROI.x + ROI.w)
        y2 = min(frame.shape[0], ROI.y + ROI.h)
        return frame[y1:y2, x1:x2]

    def _create_overview_image(self, frame: np.ndarray, result: Optional[DetectionResult]) -> np.ndarray:
        overview = frame.copy()
        cv2.rectangle(overview, (ROI.x, ROI.y), (ROI.x + ROI.w, ROI.y + ROI.h), (255, 0, 0), 2)

        if result is not None:
            gx_full = ROI.x + result.gx_roi
            gy_full = ROI.y + result.gy_roi
            wx, wy = self.homography.pixel_to_world(gx_full, gy_full)
            cv2.circle(overview, (gx_full, gy_full), 7, (0, 0, 255), -1)
            draw_text(
                overview,
                f"X={wx:.1f} Y={wy:.1f} Yaw={result.yaw_ur3e_deg:.1f}",
                (gx_full + 10, gy_full - 10),
                0.55,
                (0, 0, 255),
                2,
            )
            draw_gripper_symbol(overview, (gx_full, gy_full), result.edge_angle_deg, "Greifer")
            if self.last_eval is not None:
                draw_gripper_symbol(self.last_eval, (result.gx_roi, result.gy_roi), result.edge_angle_deg, "Greifer")

        draw_world_coordinate_system(overview, self.homography)
        return overview

    def _create_homography_image(self, overview: np.ndarray) -> np.ndarray:
        h_img = overview.copy()
        for i, (u, v) in enumerate(self.homography.pixel_points):
            cv2.circle(h_img, (int(u), int(v)), 6, (0, 0, 255), -1)
            draw_text(h_img, str(i + 1), (int(u) + 7, int(v) - 7), 0.6, (0, 0, 255), 2)
        return h_img

    def update_live_status(self) -> None:
        if self.last_result is None:
            self.status_live.setPlainText("Status: Kein Objekt erkannt. ROI, HSV-Grenzen, Beleuchtung und MIN_AREA pruefen.")
            return

        result = self.last_result
        gx_full = ROI.x + result.gx_roi
        gy_full = ROI.y + result.gy_roi
        cx_full = ROI.x + result.cx_roi
        cy_full = ROI.y + result.cy_roi
        wx, wy = self.homography.pixel_to_world(gx_full, gy_full)
        h_status = "aktiv" if self.homography.is_valid() else "Fallback mm/Pixel"

        self.status_live.setPlainText(
            f"Status: Objekt erkannt | Homographie: {h_status}\n"
            f"Pixel: Schwerpunkt=({cx_full},{cy_full})  Greifpunkt=({gx_full},{gy_full})  "
            f"Flaeche={result.area:.0f}px  Punkte={result.num_points}\n"
            f"Welt: X={wx:.1f} mm  Y={wy:.1f} mm  "
            f"Kante={result.edge_angle_deg:.1f} deg  "
            f"UR3e-Yaw={result.yaw_ur3e_deg:.1f} deg  "
            f"Schliessrichtung={result.closing_direction_deg:.1f} deg"
        )

    # ------------------------------------------------------------------
    # Homographie
    # ------------------------------------------------------------------
    def on_homography_image_clicked(self, u: int, v: int) -> None:
        if len(self.homography.pixel_points) >= 4:
            self.status_h.append("Bereits 4 Punkte vorhanden. Erst loeschen oder speichern/laden.")
            return

        if self.robot.ensure_receive_connection(self.edit_ur_ip.text().strip()):
            tcp_xyz = self.robot.get_actual_tcp_xyz_mm()
        else:
            tcp_xyz = None

        if tcp_xyz is not None:
            world_x, world_y, world_z = tcp_xyz
            self.spin_world_x.setValue(world_x)
            self.spin_world_y.setValue(world_y)
            source_text = f"UR_RTDE TCP: X={world_x:.1f} mm, Y={world_y:.1f} mm, Z={world_z:.1f} mm"
        else:
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

    def refresh_homography_table(self) -> None:
        self.table_h.setRowCount(len(self.homography.pixel_points))
        for row, ((u, v), (x, y)) in enumerate(zip(self.homography.pixel_points, self.homography.world_points)):
            for col, value in enumerate((u, v, x, y)):
                self.table_h.setItem(row, col, QtWidgets.QTableWidgetItem(f"{value:.2f}"))

    def compute_homography(self) -> None:
        if self.homography.compute():
            self.status_h.append("Homographie berechnet. Pixel->Welt ist jetzt aktiv.")
            self.status_h.append(str(self.homography.H))
        else:
            self.status_h.append("Fehler: Mindestens 4 gueltige Pixel-/Welt-Punktpaare erforderlich.")

    def clear_homography(self) -> None:
        self.homography.clear()
        self.refresh_homography_table()
        self.status_h.setPlainText("Homographiepunkte geloescht.")

    def save_homography(self) -> None:
        if not self.homography.is_valid():
            self.status_h.append("Keine gueltige Homographie zum Speichern.")
            return
        self.homography.save(WORLD.homography_file)
        self.status_h.append(f"Gespeichert: {WORLD.homography_file}")

    def load_homography(self) -> None:
        if self.homography.load(WORLD.homography_file):
            self.refresh_homography_table()
            self.status_h.append(f"Geladen: {WORLD.homography_file}")
        else:
            self.status_h.append(f"Konnte {WORLD.homography_file} nicht laden.")

    # ------------------------------------------------------------------
    # Freedrive
    # ------------------------------------------------------------------
    def toggle_freedrive(self) -> None:
        target_state = not self.robot.freedrive_enabled
        if self.robot.set_freedrive(target_state):
            if self.robot.freedrive_enabled:
                self.freedrive_blink_on = True
                self._set_freedrive_button_style(True, True)
                self.freedrive_blink_timer.start(500)
                self.status_h.append("Freedrive/Teach Mode EIN. Roboter von Hand fuehrbar.")
            else:
                self.freedrive_blink_timer.stop()
                self._set_freedrive_button_style(False)
                self.status_h.append("Freedrive/Teach Mode AUS.")

    def _set_freedrive_button_style(self, active: bool, blink_on: bool = True) -> None:
        if active:
            color = "#ffd800" if blink_on else "#806c00"
            self.btn_freedrive.setStyleSheet(f"QPushButton {{ background-color: {color}; color: black; font-weight: bold; }}")
            self.btn_freedrive.setText("Freedrive AUS")
        else:
            self.btn_freedrive.setStyleSheet("")
            self.btn_freedrive.setText("Freedrive EIN")

    def _blink_freedrive_button(self) -> None:
        if not self.robot.freedrive_enabled:
            self.freedrive_blink_timer.stop()
            self._set_freedrive_button_style(False)
            return
        self.freedrive_blink_on = not self.freedrive_blink_on
        self._set_freedrive_button_style(True, self.freedrive_blink_on)

    # ------------------------------------------------------------------
    # Roboterfunktionen
    # ------------------------------------------------------------------
    def log_robot(self, text: str) -> None:
        if hasattr(self, "status_robot"):
            self.status_robot.append(text)
        print(text)

    def connect_ur(self) -> None:
        self.robot.connect_ur(self.edit_ur_ip.text().strip())

    def disconnect_ur(self) -> None:
        if self.robot.freedrive_enabled:
            self.freedrive_blink_timer.stop()
            self._set_freedrive_button_style(False)
        self.robot.disconnect_ur()

    def connect_gripper(self) -> None:
        self.robot.connect_gripper(self.edit_gripper_ip.text().strip(), int(self.spin_gripper_port.value()))

    def require_robot_enabled(self) -> bool:
        if self.robot.freedrive_enabled:
            self.log_robot("Roboterbewegung blockiert: Freedrive/Teach Mode ist noch aktiv.")
            return False
        if not self.check_enable_robot.isChecked():
            self.log_robot("Roboterbewegung blockiert: Sicherheitscheckbox ist nicht aktiviert.")
            return False
        if self.robot.rtde_c is None:
            self.log_robot("UR_RTDE ist nicht verbunden.")
            return False
        return True

    def current_target_pose(self) -> Optional[list[float]]:
        if self.last_result is None:
            self.log_robot("Keine Objektposition erkannt.")
            return None

        result = self.last_result
        gx_full = ROI.x + result.gx_roi
        gy_full = ROI.y + result.gy_roi
        x_mm, y_mm = self.homography.pixel_to_world(gx_full, gy_full)

        x_m = x_mm / 1000.0
        y_m = y_mm / 1000.0
        z_m = float(self.spin_z.value())

        if self.check_keep_current_orientation.isChecked():
            actual_pose = self.robot.get_actual_tcp_pose()
            if actual_pose is None:
                return None
            rx, ry, rz = actual_pose[3], actual_pose[4], actual_pose[5]
        else:
            yaw_rad = math.radians(result.yaw_ur3e_deg) + float(self.spin_rz_offset.value())
            rx = float(self.spin_rx.value())
            ry = float(self.spin_ry.value())
            rz = yaw_rad

        return [x_m, y_m, z_m, rx, ry, rz]

    def lock_current_target_pose(self, purpose: str) -> Optional[tuple[list[float], list[float]]]:
        pose = self.current_target_pose()
        if pose is None:
            return None

        approach = pose.copy()
        approach[2] += float(self.spin_approach.value())
        self.locked_target_pose = pose.copy()
        self.locked_approach_pose = approach.copy()

        self.log_robot(f"{purpose} eingefroren. Greifpose [x,y,z,rx,ry,rz]: " + ", ".join(f"{v:.4f}" for v in pose))
        self.log_robot("Anfahrpose eingefroren: " + ", ".join(f"{v:.4f}" for v in approach))
        return pose, approach

    def preview_pose(self) -> None:
        pose = self.current_target_pose()
        if pose is None:
            return
        self.log_robot("Zielpose [x,y,z,rx,ry,rz]: " + ", ".join(f"{v:.4f}" for v in pose))
        self.robot.validate_pose_with_ik(pose, "Vorschau-Zielpose")
        if not self.homography.is_valid():
            self.log_robot("WARNUNG: Keine Homographie aktiv. Pixel werden nur per Fallback-Skalierung in mm umgerechnet.")

    def move_approach(self) -> None:
        if not self.require_robot_enabled():
            return
        locked = self.lock_current_target_pose("Fahrt ueber Greifpunkt")
        if locked is None:
            return
        _, approach = locked
        self.robot.move_l(approach, float(self.spin_speed.value()), float(self.spin_accel.value()), "eingefrorene Anfahrpose")

    def parse_home_joints_rad(self) -> Optional[list[float]]:
        try:
            text = self.edit_home_q.text().replace(";", ",")
            vals_deg = [float(p.strip()) for p in text.split(",") if p.strip()]
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

    def move_home(self) -> None:
        if not self.require_robot_enabled():
            return
        q_home = self.parse_home_joints_rad()
        if q_home is None:
            return
        self.robot.move_j(q_home, float(self.spin_home_speed.value()), float(self.spin_home_accel.value()), "Home")

    # ------------------------------------------------------------------
    # Pick-Zustandsautomat
    # ------------------------------------------------------------------
    def set_pick_state(self, state: PickState) -> None:
        self.pick_state = state
        self.lbl_pick_state.setText(f"Pick-Zustand: {state.name}")
        if state == PickState.IDLE:
            style = "background-color: #e8e8e8;"
        elif state == PickState.ERROR:
            style = "background-color: #ffb0b0;"
        elif state == PickState.FINISHED:
            style = "background-color: #b8ffb8;"
        else:
            style = "background-color: #fff2a8;"
        self.lbl_pick_state.setStyleSheet(f"font-weight: bold; padding: 6px; {style}")
        self.log_robot(f"Pick-Zustand -> {state.name}")

    def execute_pick_sequence(self) -> None:
        if not self.require_robot_enabled():
            return
        if self.pick_state not in (PickState.IDLE, PickState.FINISHED, PickState.ERROR):
            self.log_robot(f"Pick-Sequenz laeuft bereits: {self.pick_state.name}")
            return
        self.locked_target_pose = None
        self.locked_approach_pose = None
        self.set_pick_state(PickState.LOCK_TARGET)

    def abort_pick_sequence(self) -> None:
        self.robot.stop_motion()
        self.pick_state_busy = False
        self.set_pick_state(PickState.IDLE)
        self.log_robot("Pick-Sequenz gestoppt.")

    def run_pick_state_machine(self) -> None:
        if self.pick_state in (PickState.IDLE, PickState.ERROR) or self.pick_state_busy:
            return
        if self.pick_state == PickState.FINISHED:
            self.set_pick_state(PickState.IDLE)
            return
        if not self.require_robot_enabled():
            self.set_pick_state(PickState.ERROR)
            return

        self.pick_state_busy = True
        try:
            speed = float(self.spin_speed.value())
            accel = float(self.spin_accel.value())

            if self.pick_state == PickState.LOCK_TARGET:
                locked = self.lock_current_target_pose("Pick-Zielpose")
                if locked is None:
                    self.set_pick_state(PickState.ERROR)
                    return
                pose, approach = locked
                if not self.robot.validate_pose_with_ik(approach, "FSM-Anfahrpose"):
                    self.set_pick_state(PickState.ERROR)
                    return
                if not self.robot.validate_pose_with_ik(pose, "FSM-Greifpose"):
                    self.set_pick_state(PickState.ERROR)
                    return
                self.set_pick_state(PickState.OPEN_GRIPPER)

            elif self.pick_state == PickState.OPEN_GRIPPER:
                self.robot.move_gripper(0, speed=80, force=20)
                self.set_pick_state(PickState.MOVE_PREGRASP)

            elif self.pick_state == PickState.MOVE_PREGRASP:
                self.robot.move_l(self.locked_approach_pose, speed, accel, "FSM-Anfahrpose")
                self.set_pick_state(PickState.MOVE_GRASP)

            elif self.pick_state == PickState.MOVE_GRASP:
                self.robot.move_l(self.locked_target_pose, speed, accel, "FSM-Greifpose")
                self.set_pick_state(PickState.CLOSE_GRIPPER)

            elif self.pick_state == PickState.CLOSE_GRIPPER:
                self.robot.move_gripper(180, speed=64, force=50)
                time.sleep(0.2)
                self.set_pick_state(PickState.LIFT_OBJECT)

            elif self.pick_state == PickState.LIFT_OBJECT:
                self.robot.move_l(self.locked_approach_pose, speed, accel, "FSM-Anheben")
                self.set_pick_state(PickState.FINISHED)

        except Exception as e:
            self.robot.stop_motion()
            self.log_robot(f"Pick-FSM Fehler in Zustand {self.pick_state.name}: {e}")
            self.set_pick_state(PickState.ERROR)
        finally:
            self.pick_state_busy = False

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        try:
            if self.pipeline is not None:
                self.pipeline.stop()
            if self.robot.freedrive_enabled:
                self.robot.set_freedrive(False)
            self.robot.disconnect_ur()
            self.robot.disconnect_gripper()
        except Exception:
            pass
        event.accept()


# =============================================================================
# Start
# =============================================================================

def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
