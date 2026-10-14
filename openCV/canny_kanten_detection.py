"""PyQt6-Programm, das mit OpenCV ein Bild öffnet, es in Graustufen umwandelt, 
den Canny-Algorithmus darauf anwendet und das Ergebnis im GUI-Fenster anzeigt. 
Das Skript ermöglicht es, den unteren und oberen Schwellenwert (Threshold) interaktiv per Schieberegler zu setzen"""

import sys
import cv2
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QSlider, QFileDialog, QHBoxLayout
)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt

class CannyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Canny Kantendetektion mit OpenCV und PyQt6")
        self.image = None
        self.gray = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        btn_load = QPushButton("Bild laden")
        btn_load.clicked.connect(self.load_image)
        layout.addWidget(btn_load)

        self.label_img = QLabel("Kein Bild geladen")
        self.label_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_img)

        # Sliders für Thresholds
        slider_layout = QHBoxLayout()
        self.slider1 = QSlider(Qt.Orientation.Horizontal)
        self.slider1.setRange(0, 255)
        self.slider1.setValue(50)
        self.slider1.valueChanged.connect(self.update_canny)
        slider_layout.addWidget(QLabel("Min Threshold"))

        slider_layout.addWidget(self.slider1)

        self.slider2 = QSlider(Qt.Orientation.Horizontal)
        self.slider2.setRange(0, 255)
        self.slider2.setValue(150)
        self.slider2.valueChanged.connect(self.update_canny)
        slider_layout.addWidget(QLabel("Max Threshold"))

        slider_layout.addWidget(self.slider2)
        layout.addLayout(slider_layout)

        self.setLayout(layout)

    def load_image(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Bild öffnen", "", "Bilder (*.png *.jpg *.bmp *.jpeg)")
        if file:
            self.image = cv2.imread(file)
            self.gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
            self.update_canny()

    def update_canny(self):
        if self.gray is None:
            return
        min_val = self.slider1.value()
        max_val = self.slider2.value()
        edges = cv2.Canny(self.gray, min_val, max_val)
        h, w = edges.shape
        # Umwandlung für PyQt6-Anzeige (Graustufenbild)
        q_img = QImage(edges.data, w, h, w, QImage.Format.Format_Grayscale8)
        self.label_img.setPixmap(QPixmap.fromImage(q_img).scaled(
            400, 400, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = CannyWidget()
    win.show()
    sys.exit(app.exec())
