"""Aruco sw04 Kameraposition ermitteln.py

Ermittlung der Position einer fest montierten Kamera relativ zum Roboter-Basiskoordinatensystem. 
Dazu wird ein ArUco-Marker mit bekannter Pose (im Basiskoordinatensystem) verwendet. 
Die Kamera ermittelt die Pose des Markers relativ zur Kamera, 
und daraus wird die Pose der Kamera relativ zum Basiskoordinatensystem berechnet.
"""
# THIS FILE IS UNDER CONSTRUCTION - NOT YET FUNCTIONAL
import cv2
import numpy as np
import pyrealsense2 as rs
import time

# ============================================================
# Einstellungen
# ============================================================

MARKER_SIZE = 0.05  # Markergröße in Meter, z.B. 5 cm

# Bekannte Markerpose im Roboter-Basiskoordinatensystem
# Beispiel:
# Marker liegt 40 cm vor der Roboterbasis,
# 10 cm nach links,
# 2 cm über Tisch/Basis-Ebene.
#
# ACHTUNG:
# Diese Werte müssen Sie für Ihren Aufbau messen/kalibrieren.
BASE_MARKER_X = 0.400
BASE_MARKER_Y = 0.100
BASE_MARKER_Z = 0.020

# Orientierung des Markers im Roboter-Basiskoordinatensystem
# Roll, Pitch, Yaw in Grad
BASE_MARKER_ROLL_DEG = 0.0
BASE_MARKER_PITCH_DEG = 0.0
BASE_MARKER_YAW_DEG = 0.0

SAVE_FILE = "fixed_camera_calibration.npz"


# ============================================================
# Hilfsfunktionen
# ============================================================

def euler_deg_to_rotation_matrix(roll_deg, pitch_deg, yaw_deg):
    roll = np.deg2rad(roll_deg)
    pitch = np.deg2rad(pitch_deg)
    yaw = np.deg2rad(yaw_deg)

    Rx = np.array([
        [1, 0, 0],
        [0, np.cos(roll), -np.sin(roll)],
        [0, np.sin(roll),  np.cos(roll)]
    ])

    Ry = np.array([
        [ np.cos(pitch), 0, np.sin(pitch)],
        [0,              1, 0],
        [-np.sin(pitch), 0, np.cos(pitch)]
    ])

    Rz = np.array([
        [np.cos(yaw), -np.sin(yaw), 0],
        [np.sin(yaw),  np.cos(yaw), 0],
        [0,            0,           1]
    ])

    return Rz @ Ry @ Rx


def make_transform(x, y, z, roll_deg, pitch_deg, yaw_deg):
    T = np.eye(4)
    T[:3, :3] = euler_deg_to_rotation_matrix(
        roll_deg,
        pitch_deg,
        yaw_deg
    )
    T[:3, 3] = [x, y, z]
    return T


def rvec_tvec_to_matrix(rvec, tvec):
    R, _ = cv2.Rodrigues(rvec)

    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = tvec.flatten()

    return T


def matrix_to_xyz_rpy(T):
    R = T[:3, :3]
    x, y, z = T[:3, 3]

    sy = np.sqrt(R[0, 0]**2 + R[1, 0]**2)

    if sy > 1e-6:
        roll = np.arctan2(R[2, 1], R[2, 2])
        pitch = np.arctan2(-R[2, 0], sy)
        yaw = np.arctan2(R[1, 0], R[0, 0])
    else:
        roll = np.arctan2(-R[1, 2], R[1, 1])
        pitch = np.arctan2(-R[2, 0], sy)
        yaw = 0

    return (
        x,
        y,
        z,
        np.rad2deg(roll),
        np.rad2deg(pitch),
        np.rad2deg(yaw)
    )


def print_pose(name, T):
    x, y, z, roll, pitch, yaw = matrix_to_xyz_rpy(T)

    print()
    print(name)
    print(T)
    print(
        f"x={x:.4f} m, y={y:.4f} m, z={z:.4f} m, "
        f"roll={roll:.2f}°, pitch={pitch:.2f}°, yaw={yaw:.2f}°"
    )


# ============================================================
# Bekannte Markerpose im Roboter-Basissystem
# ============================================================

T_base_marker_known = make_transform(
    BASE_MARKER_X,
    BASE_MARKER_Y,
    BASE_MARKER_Z,
    BASE_MARKER_ROLL_DEG,
    BASE_MARKER_PITCH_DEG,
    BASE_MARKER_YAW_DEG
)

print_pose("Bekannte Pose: T_base_marker", T_base_marker_known)


# ============================================================
# RealSense starten
# ============================================================

pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(
    rs.stream.color,
    640,
    480,
    rs.format.bgr8,
    30
)

profile = pipeline.start(config)

color_profile = profile.get_stream(rs.stream.color)
intr = color_profile.as_video_stream_profile().get_intrinsics()

camera_matrix = np.array([
    [intr.fx, 0, intr.ppx],
    [0, intr.fy, intr.ppy],
    [0, 0, 1]
], dtype=np.float64)

dist_coeffs = np.array(intr.coeffs, dtype=np.float64)


# ============================================================
# ArUco vorbereiten
# ============================================================

aruco_dict = cv2.aruco.getPredefinedDictionary(
    cv2.aruco.DICT_4X4_50
)

parameters = cv2.aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(
    aruco_dict,
    parameters
)

marker_points = np.array([
    [-MARKER_SIZE / 2,  MARKER_SIZE / 2, 0],
    [ MARKER_SIZE / 2,  MARKER_SIZE / 2, 0],
    [ MARKER_SIZE / 2, -MARKER_SIZE / 2, 0],
    [-MARKER_SIZE / 2, -MARKER_SIZE / 2, 0]
], dtype=np.float64)


# ============================================================
# Hauptprogramm
# ============================================================

T_base_camera = None

print()
print("Fest montierte Kamera - Kalibrierung")
print("------------------------------------")
print("Taste s: T_base_camera berechnen und speichern")
print("Taste ESC: Beenden")
print()

try:
    while True:
        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()

        if not color_frame:
            continue

        image = np.asanyarray(color_frame.get_data())
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        corners, ids, rejected = detector.detectMarkers(gray)

        T_camera_marker = None

        if ids is not None:
            cv2.aruco.drawDetectedMarkers(image, corners, ids)

            for i, marker_id in enumerate(ids.flatten()):
                image_points = corners[i].reshape((4, 2)).astype(np.float64)

                success, rvec, tvec = cv2.solvePnP(
                    marker_points,
                    image_points,
                    camera_matrix,
                    dist_coeffs,
                    flags=cv2.SOLVEPNP_IPPE_SQUARE
                )

                if success:
                    T_camera_marker = rvec_tvec_to_matrix(rvec, tvec)

                    cv2.drawFrameAxes(
                        image,
                        camera_matrix,
                        dist_coeffs,
                        rvec,
                        tvec,
                        0.04
                    )

                    x, y, z, roll, pitch, yaw = matrix_to_xyz_rpy(
                        T_camera_marker
                    )

                    cv2.putText(
                        image,
                        f"Marker rel. Kamera: x={x:.3f} y={y:.3f} z={z:.3f}",
                        (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2
                    )

                    cv2.putText(
                        image,
                        f"r={roll:.1f} p={pitch:.1f} y={yaw:.1f}",
                        (20, 70),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2
                    )

                    break

        cv2.imshow("Fixed RealSense ArUco Calibration", image)

        key = cv2.waitKey(1) & 0xFF

        if key == 27:
            break

        elif key == ord("s"):
            if T_camera_marker is None:
                print("Kein Marker erkannt. Kalibrierung nicht möglich.")
                continue

            # Zentrale Gleichung:
            #
            # T_base_marker = T_base_camera · T_camera_marker
            #
            # Also:
            #
            # T_base_camera = T_base_marker · inv(T_camera_marker)

            T_base_camera = (
                T_base_marker_known
                @ np.linalg.inv(T_camera_marker)
            )

            print_pose("Gemessen: T_camera_marker", T_camera_marker)
            print_pose("Ergebnis: T_base_camera", T_base_camera)

            np.savez(
                SAVE_FILE,
                T_base_camera=T_base_camera,
                T_base_marker_known=T_base_marker_known,
                camera_matrix=camera_matrix,
                dist_coeffs=dist_coeffs
            )

            print()
            print(f"Kalibrierung gespeichert in: {SAVE_FILE}")

            time.sleep(0.5)

finally:
    pipeline.stop()
    cv2.destroyAllWindows()