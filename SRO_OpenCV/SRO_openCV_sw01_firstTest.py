# SRO_openCV_sw01_firstTest.py
# ................................
# Tested by OJ am 15.11.24 
# python 3.12.7
#-------------------------------------
# ggf. python.exe -m pip install --upgrade pip
# ggf. pip install opencv-python
import cv2 as cv

# initialisiere WebCam
cam = cv.VideoCapture(0)

# WebCam braucht einen Moment zum Starten
# und zum Einstellen des Autofokus
# => ggf. mehrere Bilder holen und die ersten verwerfen

# lese ein Bild von der WebCam
# ret, image = cam.read()
# ret, image = cam.read()
ret, image = cam.read()

# zeige das Bild an
cv.imshow("WebCam", image)
cv.waitKey(0)

# konvertiere das Bild in Graustufen
image = cv.cvtColor(image, cv.COLOR_BGR2GRAY)

# zeige das Bild an
cv.imshow("Bild modifiziert", image)
cv.waitKey(0) 

cv.destroyAllWindows()
