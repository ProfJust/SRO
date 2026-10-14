# SRO_openCV_sw03_Pixel_Linie.py
# .......................................
# Tested and edited for WHS by OJ at 15.11.2024

import cv2
import os
image_path = r'C:\mySciebo\_SRO\UR_Programme PC Python RTDE\SRO_OpenCV\bild_von_webcam.png'
filename = 'pixel_line.jpg'

# Einlesen
image = cv2.imread(image_path)

# Verarbeitung
# lese Farbwerte an Position y, x
y = 450
x = 200
(b, g, r) = image[y, x]

# gib Farbwerte auf Bildschirm aus
print(" Farbwert des Pixels (B,G,R)")
print(b, g, r)

# Zeichne rote Linie (im BGR-Farbraum)
for x in range(200, 400):
    image[y, x] = (0, 0, 255)

# zeige Bild in Fenster an
cv2.imshow("Bild", image)
# Ausgabe
cv2.imwrite(filename, image)

cv2.waitKey(0) 
