import cv2
import numpy as np
import pyrealsense2 as rs

# frame = Farbbild der Kamera, z.B. von RealSense
hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

# Beispiel: rotes Objekt
lower_red1 = np.array([0, 80, 50])
upper_red1 = np.array([10, 255, 255])
lower_red2 = np.array([170, 80, 50])
upper_red2 = np.array([180, 255, 255])

mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
mask = mask1 + mask2

# Rauschen entfernen
kernel = np.ones((5, 5), np.uint8)
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

# Konturen suchen
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

if contours:
    c = max(contours, key=cv2.contourArea)

    M = cv2.moments(c)

    if M["m00"] != 0:
        u = int(M["m10"] / M["m00"])
        v = int(M["m01"] / M["m00"])

        print("Schwerpunkt Pixel:", u, v)

        cv2.circle(frame, (u, v), 8, (0, 255, 0), -1)
        cv2.drawContours(frame, [c], -1, (255, 0, 0), 2)

    depth = depth_frame.get_distance(u, v)  # Meter
    print("Tiefe:", depth)


    # Pixelkoordinate in 3D-Kamerakoordinate umrechnen
    point_3d = rs.rs2_deproject_pixel_to_point(
        depth_intrinsics,
        [u, v],
        depth
    )

    Xc, Yc, Zc = point_3d  #Xc, Yc, Zc in Meter im Koordinatensystem der Kamera
    print("Kamerakoordinate:", Xc, Yc, Zc)