import sys
import cv2
import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets


class VideoWidget(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(640, 480)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("HSV Farbtracker (PyQt6 + OpenCV)")
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # ggf. CAP_DSHOW unter Windows weglassen

        # Default HSV-Bereiche (z.B. für „grünähnlich“)
        self.h_min = 40
        self.s_min = 40
        self.v_min = 40
        self.h_max = 80
        self.s_max = 255
        self.v_max = 255

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        self.video_label = VideoWidget()

        sliders_layout = QtWidgets.QGridLayout()
        self.sliders = {}

        def add_slider(row, name, min_val, max_val, start_val, callback):
            label = QtWidgets.QLabel(name)
            slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            slider.setRange(min_val, max_val)
            slider.setValue(start_val)
            slider.valueChanged.connect(callback)
            value_label = QtWidgets.QLabel(str(start_val))

            # Wertanzeige aktualisieren
            slider.valueChanged.connect(lambda v, lbl=value_label: lbl.setText(str(v)))

            sliders_layout.addWidget(label, row, 0)
            sliders_layout.addWidget(slider, row, 1)
            sliders_layout.addWidget(value_label, row, 2)

            self.sliders[name] = slider

        add_slider(0, "H_min", 0, 179, self.h_min, self.on_h_min_changed)
        add_slider(1, "H_max", 0, 179, self.h_max, self.on_h_max_changed)
        add_slider(2, "S_min", 0, 255, self.s_min, self.on_s_min_changed)
        add_slider(3, "S_max", 0, 255, self.s_max, self.on_s_max_changed)
        add_slider(4, "V_min", 0, 255, self.v_min, self.on_v_min_changed)
        add_slider(5, "V_max", 0, 255, self.v_max, self.on_v_max_changed)

        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.addWidget(self.video_label)
        main_layout.addLayout(sliders_layout)

        # Timer für Video-Update
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # ~33fps

    # Slider-Callbacks
    def on_h_min_changed(self, value):
        self.h_min = value

    def on_h_max_changed(self, value):
        self.h_max = value

    def on_s_min_changed(self, value):
        self.s_min = value

    def on_s_max_changed(self, value):
        self.s_max = value

    def on_v_min_changed(self, value):
        self.v_min = value

    def on_v_max_changed(self, value):
        self.v_max = value

    def update_frame(self):
        if not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if not ret:
            return

        # Bild spiegeln (optional, „Spiegelmodus“)
        frame = cv2.flip(frame, 1)

        # BGR → HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        lower = np.array([self.h_min, self.s_min, self.v_min], dtype=np.uint8)
        upper = np.array([self.h_max, self.s_max, self.v_max], dtype=np.uint8)

        # Maske und Objektfindung
        mask = cv2.inRange(hsv, lower, upper)
        # etwas rauschen reduzieren
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.erode(mask, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            # größtes Objekt nehmen
            c = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(c)
            if area > 500:  # Schwellwert, um kleine Flecken zu ignorieren
                # Kontur zeichnen
                cv2.drawContours(frame, [c], -1, (0, 255, 0), 2)

                M = cv2.moments(c)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    # Schwerpunkt markieren
                    cv2.circle(frame, (cx, cy), 7, (0, 0, 255), -1)
                    cv2.putText(frame, f"({cx},{cy})", (cx + 10, cy - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

        # nach RGB für Qt
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qimg = QtGui.QImage(rgb_image.data, w, h, bytes_per_line,
                            QtGui.QImage.Format.Format_RGB888)
        pixmap = QtGui.QPixmap.fromImage(qimg)

        self.video_label.setPixmap(pixmap)

    def closeEvent(self, event):
        # Kamera freigeben
        if self.cap.isOpened():
            self.cap.release()
        super().closeEvent(event)


def main():
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
