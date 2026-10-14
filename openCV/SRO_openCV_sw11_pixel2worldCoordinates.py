# SRO_openCV_sw11_pixel2worldCoordinates.py
# ................................
# Tested by OJ am 16.3.26 
# python 3.12.7
# Bildkoordinaten (u,v) in Pixeln
# in reale Tischkoordinaten (x,y) in mm umrechnen
# dazu Homographie-Matrix ermitteln und Bildpunkte transofrmieren
# -------------------------------------

import cv2
import numpy as np

# Vier bekannte Bildpunkte der Tischplatte / Kalibrierplatte
#  in Pixelkoordinaten (u,v)
img_pts = np.array([
    [512, 213],
    [1089, 226],
    [1075, 712],
    [498, 695]
], dtype=np.float32)

# Zugehörige reale Tischkoordinaten in mm (Roboterkoordinaten)
table_pts = np.array([
    [0.0,   0.0],
    [300.0, 0.0],
    [300.0, 200.0],
    [0.0,   200.0]
], dtype=np.float32)

# Homographie Bild -> Tisch
# Berechnung der Homographie-Matrix H, die die Transformation von Bildpunkten zu Tischpunkten beschreibt
# RANSAC-Algorithmus wird verwendet, um die Berechnung robust gegen Ausreißer zu machen
# H ist eine 3x3 Matrix, die die Beziehung zwischen den Bildkoordinaten und den Tischkoordinaten beschreibt
#   Die Funktion cv2.findHomography() gibt die Homographie-Matrix H zurück, die die Transformation von den Bildpunkten (img_pts) zu den Tischpunkten (table_pts) beschreibt.
#  https://docs.opencv.org/4.x/d1/de0/tutorial_py_feature_homography.html?utm_source=chatgpt.com
H, mask = cv2.findHomography(img_pts, table_pts, cv2.RANSAC, 3.0)
print("Homographie-Matrix H:")
print(H)
# Beispiel: detektierter Greifpunkt im Bild in Pixelkoordinaten (u,v)
pick_uv = np.array([[[820.0, 430.0]]], dtype=np.float32)

# Umrechnung in Tischkoordinaten (x,y) in mm
pick_xy = cv2.perspectiveTransform(pick_uv, H) # Ergebnis ist ein 1x1x2 Array mit (x,y) in mm

u = float(pick_uv[0,0,0])
v = float(pick_uv[0,0,1])
print(f"Bildkoordinaten: u={u:.1f}, v={v:.1f}")

x_table = float(pick_xy[0, 0, 0]) # x-Koordinate in mm
y_table = float(pick_xy[0, 0, 1]) # y-Koordinate in mm
print(f"Tischkoordinate: x={x_table:.1f} mm, y={y_table:.1f} mm")

"""# ggf. python.exe -m pip install --upgrade pip
# ggf. pip install opencv-python
import cv2 as cv

# initialisiere WebCam
CAMERA_INDEX = 0
cam = cv.VideoCapture(CAMERA_INDEX, cv.CAP_DSHOW) 
# cv.CAP_DSHOW => dauert nicht so lange bis Bild von USB-Kamera kommt


# WebCam braucht einen Moment zum Starten
# und zum Einstellen des Autofokus
# => ggf. mehrere Bilder holen und die ersten verwerfen

# lese ein Bild von der WebCam
ret, image = cam.read()
ret, image = cam.read()


ret, image = cam.read()

# zeige das Bild an
print("Lese Bild von Kamera und zeige es an ")
cv.imshow("WebCam", image)
print("Kamera initialisiert, in Fenster klicken und Taste drücken")
cv.waitKey(0)



cv.destroyAllWindows()

###### # Beispiel für die Berechnung der Homographie-Matrix H

H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

src_pts und dst_pts sind korrespondierende 2D-Punkte, RANSAC macht die Schätzung robust gegen Ausreißer, und mask sagt Ihnen, welche Punktpaare als Inlier akzeptiert wurden."""