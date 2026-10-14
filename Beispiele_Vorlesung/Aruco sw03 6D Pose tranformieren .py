"""Aruco-Marker erkennen und dessen Pose zur Roboterbasis berechnen
Dazu muss die Pose der Kamera relativ zur Roboterbasis bekannt  sein

# Beispiel: Kamera relativ zur Roboterbasis
        # Werte müssen Sie kalibrieren oder messen!
        T_base_camera = np.array([
            [1, 0, 0, 0.300],
            [0, 1, 0, 0.000],
            [0, 0, 1, 0.500],
            [0, 0, 0, 1.000]
        ])
"""
# THIS FILE IS UNDER CONSTRUCTION - NOT YET FUNCTIONAL
import cv2
print("Nutze OpenCV Version:", cv2.__version__)
import numpy as np
import pyrealsense2 as rs
import time

def pose_to_matrix(rvec, tvec):
    R, _ = cv2.Rodrigues(rvec)

    T = np.eye(4)
    T[0:3, 0:3] = R
    T[0:3, 3] = tvec.flatten()

    return T


def matrix_to_pose(T):
    R = T[0:3, 0:3]
    t = T[0:3, 3]

    rvec, _ = cv2.Rodrigues(R)

    return rvec, t

MARKER_SIZE = 0.05  # Marker-Kantenlänge in Meter, z.B. 5 cm
# Diese Größe muss exakt zum ausgedruckten Marker passen. Sonst ist die berechnete Entfernung falsch.
# Aruco Printer: https://chev.me/arucogen/
# https://pyimagesearch.com/2020/12/21/detecting-aruco-markers-with-opencv-and-python/?utm_source=chatgpt.com

# RealSense starten
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

# Kameraparameter auslesen
"""fx, fy = Brennweiten in Pixeln
ppx, ppy = Bildmittelpunkt / principal point
coeffs = Verzeichnungsparameter"""
profile = pipeline.start(config)
color_profile = profile.get_stream(rs.stream.color)
intr = color_profile.as_video_stream_profile().get_intrinsics()

# Transformationsmatrix aufbauen
camera_matrix = np.array([
    [intr.fx, 0, intr.ppx],
    [0, intr.fy, intr.ppy],
    [0, 0, 1]
], dtype=np.float32)

dist_coeffs = np.array(intr.coeffs, dtype=np.float32)

# ArUco-Detektor
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50) 
parameters = cv2.aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)

try:
    while True:
        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        if not color_frame:
            continue

        # Bild in OpenCV-Format umwandeln
        image = np.asanyarray(color_frame.get_data())
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Marker erkennen
        corners, ids, rejected = detector.detectMarkers(gray)

        if ids is not None:
            # Erkannte Marker einzeichnen
            cv2.aruco.drawDetectedMarkers(image, corners, ids)
            # Pose berechnen
            #  rvec = Rotation des Markers relativ zur Kamera
            #  tvec = Verschiebung des Markers relativ zur Kamera
            """rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(
                corners, MARKER_SIZE, camera_matrix, dist_coeffs
            )"""

            marker_points = np.array([
                [-MARKER_SIZE/2,  MARKER_SIZE/2, 0],
                [ MARKER_SIZE/2,  MARKER_SIZE/2, 0],
                [ MARKER_SIZE/2, -MARKER_SIZE/2, 0],
                [-MARKER_SIZE/2, -MARKER_SIZE/2, 0]
            ], dtype=np.float32)

            for i, marker_id in enumerate(ids.flatten()):
                image_points = corners[i].reshape((4, 2)).astype(np.float32)

                success, rvec, tvec = cv2.solvePnP(
                    marker_points,
                    image_points,
                    camera_matrix,
                    dist_coeffs,
                    flags=cv2.SOLVEPNP_IPPE_SQUARE
                )

                if success:
                    cv2.drawFrameAxes(
                        image,
                        camera_matrix,
                        dist_coeffs,
                        rvec,
                        tvec,
                        0.05  # Größe des Koordinatenkreuzes
                    )

        # Translation in Meter
        x, y, z = tvec.flatten()

        # Rotation: rvec -> Rotationsmatrix
        R, _ = cv2.Rodrigues(rvec)

        # Rotationsmatrix -> Euler-Winkel Roll, Pitch, Yaw
        sy = np.sqrt(R[0, 0]**2 + R[1, 0]**2)

        if sy > 1e-6:
            roll  = np.arctan2(R[2, 1], R[2, 2])
            pitch = np.arctan2(-R[2, 0], sy)
            yaw   = np.arctan2(R[1, 0], R[0, 0])
        else:
            roll  = np.arctan2(-R[1, 2], R[1, 1])
            pitch = np.arctan2(-R[2, 0], sy)
            yaw   = 0

        # rad -> Grad
        roll_deg  = np.degrees(roll)
        pitch_deg = np.degrees(pitch)
        yaw_deg   = np.degrees(yaw)

        print(
            f"ID {marker_id}: "
            f"x={x:.3f} m, y={y:.3f} m, z={z:.3f} m, "
            f"roll={roll_deg:.1f}°, pitch={pitch_deg:.1f}°, yaw={yaw_deg:.1f}°"
        )

        cv2.imshow("RealSense ArUco Pose", image)
        time.sleep(1)

        if cv2.waitKey(1) & 0xFF == 27:  # ESC
            break

        # Markerpose relativ zur Kamera
        T_camera_marker = pose_to_matrix(rvec, tvec)

        # Beispiel: Kamera relativ zur Roboterbasis
        # Werte müssen Sie kalibrieren oder messen!
        T_base_camera = np.array([
            [1, 0, 0, 0.300],
            [0, 1, 0, 0.000],
            [0, 0, 1, 0.500],
            [0, 0, 0, 1.000]
        ])

        # Markerpose relativ zur Roboterbasis
        T_base_marker = T_base_camera @ T_camera_marker

        rvec_base_marker, t_base_marker = matrix_to_pose(T_base_marker)

        print("Marker relativ zur Roboterbasis:")
        print(f"x = {t_base_marker[0]:.3f} m")
        print(f"y = {t_base_marker[1]:.3f} m")
        print(f"z = {t_base_marker[2]:.3f} m")


finally:
    pipeline.stop()
    cv2.destroyAllWindows()