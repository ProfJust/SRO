"""Wie Sie es nutzen

Ein Bild Ihres Objekts aufnehmen (z.B. object_template.jpg)

Möglichst frontal, gute Beleuchtung.

Skript speichern: object_detection_pyqt.py

Pfad zu TEMPLATE_PATH anpassen.

Starten:"""
import sys
import cv2
import numpy as np

from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QMessageBox
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap


# Pfad zum Referenzbild (Foto des Objekts, das Sie erkennen wollen)
TEMPLATE_PATH = "foto02_roi.jpg"   # <- anpassen


class ObjectDetectorWindow(QMainWindow):
    def __init__(self, camera_index=0, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Objekterkennung mit ORB + Homographie (PyQt6 + OpenCV)")
        self.resize(960, 720)

        # Video-Anzeige
        self.label = QLabel("Starte Kamera...", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(self.label)

        # Kamera öffnen
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            QMessageBox.critical(self, "Fehler", "Kamera konnte nicht geöffnet werden.")
            sys.exit(1)

        # ORB-Detektor und Matcher vorbereiten
        self.orb = cv2.ORB_create(
            nfeatures=1500,
            scaleFactor=1.2,
            nlevels=8,
            edgeThreshold=31,
            patchSize=31
        )
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

        # Referenzbild laden und Features berechnen
        self.template_img_color, self.template_kp, self.template_des = self.load_template(TEMPLATE_PATH)
        if self.template_img_color is None:
            QMessageBox.critical(self, "Fehler", f"Referenzbild '{TEMPLATE_PATH}' konnte nicht geladen werden.")
            sys.exit(1)

        # Template-Eckpunkte (in Template-Koordinaten)
        h, w = self.template_img_color.shape[:2]
        self.template_corners = np.float32(
            [[0, 0],
             [w - 1, 0],
             [w - 1, h - 1],
             [0, h - 1]]
        ).reshape(-1, 1, 2)

        # Timer für Livebild
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # ca. 30 fps

    def load_template(self, path):
        """
        Referenzbild laden und ORB-Features berechnen.
        """
        img_color = cv2.imread(path, cv2.IMREAD_COLOR)
        if img_color is None:
            return None, None, None

        img_gray = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)
        kp, des = self.orb.detectAndCompute(img_gray, None)
        print(f"[INFO] Template: {len(kp)} Keypoints gefunden")
        return img_color, kp, des

    def update_frame(self):
        """
        Wird vom QTimer zyklisch aufgerufen:
        - Frame von der Kamera holen
        - Objekterkennung durchführen
        - Ergebnisbild im QLabel anzeigen
        """
        ret, frame = self.cap.read()
        if not ret:
            return

        frame_draw = frame.copy()

        # Graubild für Feature-Erkennung
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Keypoints und Deskriptoren im aktuellen Frame berechnen
        kp_frame, des_frame = self.orb.detectAndCompute(gray, None)

        if des_frame is not None and self.template_des is not None and len(des_frame) > 0:
            # k-Nächste-Nachbarn-Matching (k=2) für Ratio-Test
            matches = self.matcher.knnMatch(self.template_des, des_frame, k=2)

            good_matches = []
            for m, n in matches:
                # Lowe's Ratio-Test
                if m.distance < 0.75 * n.distance:
                    good_matches.append(m)

            # Debug-Ausgabe
            # print(f"Matches: {len(matches)}, gute Matches: {len(good_matches)}")

            # Nur wenn ausreichend gute Matches vorhanden sind, Homographie schätzen
            MIN_MATCH_COUNT = 15
            if len(good_matches) >= MIN_MATCH_COUNT:
                # Quell- (Template) und Zielpunkte (Frame)
                src_pts = np.float32([self.template_kp[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                dst_pts = np.float32([kp_frame[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

                # Homographie berechnen (RANSAC für Robustheit)
                H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

                if H is not None:
                    # Template-Eckpunkte in das Kamerabild projizieren
                    dst_corners = cv2.perspectiveTransform(self.template_corners, H)

                    # Polygon (Umriss des erkannten Objekts) einzeichnen
                    frame_draw = cv2.polylines(
                        frame_draw,
                        [np.int32(dst_corners)],
                        isClosed=True,
                        color=(0, 255, 0),
                        thickness=3
                    )

                    cv2.putText(
                        frame_draw,
                        f"Objekt erkannt ({len(good_matches)} Matches)",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.0,
                        (0, 255, 0),
                        2,
                        cv2.LINE_AA
                    )
                else:
                    cv2.putText(
                        frame_draw,
                        f"Keine gueltige Homographie ({len(good_matches)} Matches)",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.0,
                        (0, 0, 255),
                        2,
                        cv2.LINE_AA
                    )
            else:
                cv2.putText(
                    frame_draw,
                    f"Zu wenige Matches: {len(good_matches)}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA
                )
        else:
            cv2.putText(
                frame_draw,
                "Keine Features im Frame gefunden",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 0, 255),
                2,
                cv2.LINE_AA
            )

        # OpenCV BGR -> Qt QImage (BGR888)
        h, w, ch = frame_draw.shape
        bytes_per_line = ch * w
        qimg = QImage(frame_draw.data, w, h, bytes_per_line, QImage.Format.Format_BGR888)
        pixmap = QPixmap.fromImage(qimg)

        # Bild ins Label setzen (ggf. skalieren)
        self.label.setPixmap(pixmap.scaled(
            self.label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))

    def closeEvent(self, event):
        """
        Aufräumen beim Schließen des Fensters.
        """
        if self.cap.isOpened():
            self.cap.release()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    window = ObjectDetectorWindow(camera_index=0)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
