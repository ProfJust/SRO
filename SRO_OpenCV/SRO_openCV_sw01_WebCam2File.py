# SRO_openCV_sw01_WebCam2File.py
# ................................
# Tested by OJ am 15.11.24

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
