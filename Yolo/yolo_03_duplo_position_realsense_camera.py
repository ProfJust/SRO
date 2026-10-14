# Falls eine Intel RealSense verwendet wird,
# ist cv2.VideoCapture() oft nicht der richtige Weg
# Dann sollten Sie pyrealsense2 verwenden und das RealSense-Bild 
# an YOLO übergeben.
# pip install pyrealsense2

# Für Yolo und OpenCV:
# pip install opencv-python ultralytics pyrealsense2

from ultralytics import YOLO
import pyrealsense2 as rs
import numpy as np
import cv2
import math
import os

# Arbeitsordner auf Skriptordner setzen
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# YOLO-Modell laden
model = YOLO("./yolov8_duplo_custom9/weights/best.pt")

# Objektklassen
classNames = ["duplo_4_green"]

# RealSense initialisieren
pipeline = rs.pipeline()
config = rs.config()

# Farbbild aktivieren: 640x480, BGR, 30 FPS
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

print("RealSense Kamera wird gestartet...")
pipeline.start(config)
print("RealSense Kamera gestartet")

try:
    while True:
        # Frames von RealSense holen
        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()

        if not color_frame:
            print("Kein Farbbild erhalten")
            continue

        # RealSense Frame in OpenCV-Bild umwandeln
        img = np.asanyarray(color_frame.get_data())

        # YOLO ausführen
        results = model(img, stream=True)

        for r in results:
            boxes = r.boxes

            for box in boxes:
                # Bounding Box
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 255), 3)

                # Mittelpunkt berechnen
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)

                print("Mittelpunkt Duplo:", cx, cy)

                cv2.circle(img, (cx, cy), 5, (0, 255, 0), -1)

                # Confidence
                confidence = math.ceil(float(box.conf[0]) * 100) / 100
                print("Confidence --->", confidence)

                # Klasse
                cls = int(box.cls[0])

                if cls < len(classNames):
                    label = classNames[cls]
                else:
                    label = f"Klasse {cls}"

                print("Class name -->", label)

                cv2.putText(
                    img,
                    f"{label} {confidence}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255, 0, 0),
                    2
                )

        cv2.imshow("RealSense YOLO Duplo", img)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

except KeyboardInterrupt:
    print("Programm mit STRG+C beendet")

finally:
    pipeline.stop()
    cv2.destroyAllWindows()
    print("RealSense Kamera gestoppt")