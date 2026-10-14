# SRO_openCV_sw01_WebCam2File.py
# ................................
# Tested by OJ am 09.11.25
# Erweiterung: Maus-ROI-Auswahl vor dem Speichern

"""Kurz zusammengefasst:

Sie sehen erst das Kamerabild.

Mit der Maus ziehen Sie ein Rechteck.

Nach Enter/Space wird dieser Ausschnitt als foto02_roi.jpg gespeichert.

Wenn Sie abbrechen (c drücken oder nichts auswählen), wird wie früher foto02.jpg mit dem kompletten Bild gespeichert."""

# ggf. pip install opencv-python
import cv2 as cv

print("Lese Bild von Kamera und speichere als Datei ")
# -- initialisiere WebCam --
CAMERA_INDEX = 0
cam = cv.VideoCapture(CAMERA_INDEX, cv.CAP_DSHOW)  # cv.CAP_DSHOW => dauert nicht so lange bis Bild von USB-Kamera kommt
if not cam.isOpened():
    print("Kamera kann nicht geöffnet werden!")
    exit()

print("Kamera initialisiert")

# lese ein Bild von der WebCam
ret, img = cam.read()
cam.release()  # Kamera gleich wieder freigeben, wir brauchen nur ein Bild

if not ret or img is None:
    print("Fehler: Kein Bild von der Kamera gelesen!")
    exit()

# Fenster erzeugen und Bild anzeigen
cv.namedWindow("WebCam", cv.WINDOW_NORMAL)
cv.imshow("WebCam", img)

print("Wählen Sie mit der Maus einen Bereich im Bild aus.")
print("Bedienung:")
print("  - Linke Maustaste ziehen: Rechteck aufziehen")
print("  - Enter / Space: Auswahl bestätigen und zuschneiden")
print("  - c-Taste: Auswahl abbrechen (ganzes Bild wird gespeichert)")

# ROI-Auswahl: (x, y, w, h)
roi = cv.selectROI("WebCam", img, showCrosshair=True, fromCenter=False)

x, y, w, h = roi

if w > 0 and h > 0:
    # Benutzer hat einen gültigen Bereich gewählt
    cropped = img[int(y):int(y + h), int(x):int(x + w)]
    cv.imshow("Auswahl", cropped)
    print("Ausschnitt ausgewählt. Drücken Sie eine Taste, um zu speichern.")
    cv.waitKey(0)

    filename = 'foto02_roi.jpg'
    cv.imwrite(filename, cropped)
    print("Ausschnitt gespeichert als:", filename)
else:
    # Keine oder abgebrochene Auswahl -> ganzes Bild speichern
    print("Keine gültige Auswahl – speichere das komplette Bild.")
    filename = 'foto02.jpg'
    cv.imwrite(filename, img)
    print("Bild gespeichert:", filename)

cv.destroyAllWindows()
