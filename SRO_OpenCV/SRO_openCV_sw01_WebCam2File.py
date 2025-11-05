# SRO_openCV_sw01_WebCam2File.py
# ................................
# Tested by OJ am 15.11.24

# ggf. pip install opencv-python
import cv2 as cv


print("Lese Bild von Kamera und speichere als Datei ")
# initialisiere WebCam
CAMERA_INDEX = 0
cam = cv.VideoCapture(CAMERA_INDEX, cv.CAP_DSHOW) 
# cv.CAP_DSHOW => dauert nicht so lange bis Bild von USB-Kamera kommt
print("Kamera initialisiert")

# WebCam braucht einen Moment zum Starten
# und zum Einstellen des Autofokus
# => ggf. mehrere Bilder holen und die ersten verwerfen


# lese ein Bild von der WebCam
ret, dummy = cam.read()
ret, dummy = cam.read()
ret, img = cam.read()

# zeige das Bild an
cv.imshow("WebCam", img)
cv.waitKey(0)

# speichere das Bild ab
# Filename
filename = 'foto01.jpg'
# Using cv2.imwrite() method
# Saving the image
cv.imwrite(filename, img)

cv.destroyAllWindows()
