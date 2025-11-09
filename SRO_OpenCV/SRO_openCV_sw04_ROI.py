# SRO_openCV_sw04_ROI.py
# .......................................
# Python program to explain Region of Interes ROI
# .......................................
# edited WHS, OJ, 09.11.2025
import cv2 as cv

# lese Bild von Festplatte
img = cv.imread(r'C:\mySciebo\_SRO\UR_Programme PC Python RTDE\SRO_OpenCV\bild_von_webcam.png')
y = 380; x = 440
# waehle eine Region of Interest an Punkt:
# (y, x) mit Dimension 50x50 Pixel
region_of_interest = img[y:y+90, x:x+180]
# zeige Region of Interest an
cv.imshow("ROI", region_of_interest)
# warte auf Tastendruck (wichtig, sonst sieht man das Fenster nicht)
cv.waitKey(0)

# setze ROI auf Gruen
region_of_interest[:, :] = (0, 255, 0)
# die ROI ist ein "Zeiger" auf das urspruenglich geladene Image.
# Es enthaelt nun eine gruene Box!
cv.imshow("Bild modifiziert", img)

# warte auf Tastendruck
cv.waitKey(0)
