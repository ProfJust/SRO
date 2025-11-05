# SRO_openCV_sw01_firstTest.py
# ................................
# Tested by OJ am 9.5.25 
# python 3.12.7
# WebCam anschliessen
#-------------------------------------
# ggf. python.exe -m pip install --upgrade pip
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

# konvertiere das Bild in Graustufen
image = cv.cvtColor(image, cv.COLOR_BGR2GRAY)

# zeige das Bild an
cv.imshow("Bild modifiziert", image)
cv.waitKey(0) 

cv.destroyAllWindows()
