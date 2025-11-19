# SRO_openCV_sw01_WebCam2File.py
# ................................
# Tested by OJ am 09.11.25

# ggf. pip install opencv-python
import cv2 as cv

print("Lese Bild von Kamera und speichere als Datei ")
# -- initialisiere WebCam --
CAMERA_INDEX = 0
cam = cv.VideoCapture(CAMERA_INDEX, cv.CAP_DSHOW) # cv.CAP_DSHOW => dauert nicht so lange bis Bild von USB-Kamera kommt
if not cam.isOpened():
    print("Kamera kann nicht geöffnet werden!")
    exit()

print("Kamera initialisiert")

# lese ein Bild von der WebCam
ret, img = cam.read()

# zeige das Bild an
cv.imshow("WebCam", img)
cv.waitKey(0)

# -- speichere das Bild ab --
filename = 'foto02.jpg'
cv.imwrite(filename, img)  # Saving the image
print(" Bild gespeichert:", filename)
cv.destroyAllWindows()
