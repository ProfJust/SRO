import numpy as np
import cv2
import pyrealsense2 as rs
from scipy.spatial.transform import Rotation as R
import rtde_control
import rtde_receive

# ---------------- Konfiguration ----------------

ROBOT_IP       = "192.168.0.10"
MARKER_ID      = 0              # gesuchte ArUco-ID
MARKER_LENGTH  = 0.04           # Marker-Kantenlänge in m
APPROACH_DIST  = 0.05           # 5 cm über Objekt anfahren

# Datei-Pfade zu Kalibrierergebnissen
CAMERA_MATRIX_FILE = "camera_matrix.npy"
DIST_COEFFS_FILE   = "dist_coeffs.npy"
T_BASE_CAM_FILE    = "T_base_cam.npy"   # 4x4

# ------------------------------------------------
# Hilfsfunktionen
# ------------------------------------------------

def make_T(Rm, t):
    T = np.eye(4)
    T[:3, :3] = Rm
    T[:3,  3] = t
    return T

def pose_from_T(T):
    Rm = T[:3, :3]
    t  = T[:3, 3]
    rv = R.from_matrix(Rm).as_rotvec()
    return [float(t[0]), float(t[1]), float(t[2]),
            float(rv[0]), float(rv[1]), float(rv[2])]

def aruco_detector():
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    parameters = cv2.aruco.DetectorParameters()
    detector   = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    return detector

# ------------------------------------------------
# Init: Kamera, ArUco, UR-RTDE
# ------------------------------------------------

# Kamera-Parameter laden
camera_matrix = np.load(CAMERA_MATRIX_FILE)
dist_coeffs   = np.load(DIST_COEFFS_FILE)

# Transformation Base -> Cam laden
T_base_cam = np.load(T_BASE_CAM_FILE)

# Greifer-Offset: TCP soll beim Greifen z.B. 5 cm über Marker-Zentrum sein,
# und TCP-z-Achse entlang Marker-z zeigen (hier Identität + -Z-Offset als Beispiel).
R_obj_tcp = np.eye(3)
t_obj_tcp = np.array([0.0, 0.0, -APPROACH_DIST])
T_obj_tcp = make_T(R_obj_tcp, t_obj_tcp)

# Realsense initialisieren (Farbstrom)
pipeline = rs.pipeline()
config   = rs.config()
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
pipeline.start(config)

detector = aruco_detector()

# UR RTDE
rtde_ctrl = rtde_control.RTDEControlInterface(ROBOT_IP)
rtde_rec  = rtde_receive.RTDEReceiveInterface(ROBOT_IP)

# ------------------------------------------------
# Hauptschleife: Marker suchen, Pose berechnen, UR bewegen
# ------------------------------------------------

try:
    while True:
        # Frames holen
        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        if not color_frame:
            continue

        color_image = np.asanyarray(color_frame.get_data())
        gray        = cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY)

        corners, ids, rejected = detector.detectMarkers(gray)

        if ids is not None:
            # Prüfen, ob gewünschter Marker dabei ist
            ids = ids.flatten()
            for i, marker_id in enumerate(ids):
                if marker_id != MARKER_ID:
                    continue

                # Pose im Kameraframe schätzen
                rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(
                    [corners[i]],
                    MARKER_LENGTH,
                    camera_matrix,
                    dist_coeffs
                )
                rvec = rvecs[0][0]
                tvec = tvecs[0][0]

                R_cam_marker, _ = cv2.Rodrigues(rvec)
                t_cam_marker    = tvec  # [m]

                T_cam_marker = make_T(R_cam_marker, t_cam_marker)

                # Objekt = Markerzentrum (ohne zusätzlichen Offset)
                T_marker_obj = np.eye(4)

                # Objektpose im Basisframe
                T_base_obj = T_base_cam @ T_cam_marker @ T_marker_obj

                # TCP-Zielpose (z.B. direkt über Objekt mit Greifer-Offset)
                T_base_tcp_target = T_base_obj @ T_obj_tcp

                tcp_target = pose_from_T(T_base_tcp_target)

                # debug-Ausgabe
                print("Marker-ID:", marker_id)
                print("TCP-Target:", tcp_target)

                # Visualisierung
                cv2.aruco.drawAxis(color_image, camera_matrix, dist_coeffs,
                                   rvec, tvec, MARKER_LENGTH * 0.5)
                cv2.aruco.drawDetectedMarkers(color_image, [corners[i]])

                # Roboterbewegung (lineare Bewegung im Baseframe)
                speed = 0.1
                acc   = 0.3
                # UR-RTDE moveL erwartet [x,y,z,rx,ry,rz,speed,acc] oder separat
                rtde_ctrl.moveL(tcp_target, speed, acc)

                # Für Testzwecke nur einmal fahren:
                # break   # optional, um nach einem Move die Schleife zu verlassen

        cv2.imshow("Realsense ArUco", color_image)
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break

finally:
    pipeline.stop()
    cv2.destroyAllWindows()
    rtde_ctrl.stopScript()
