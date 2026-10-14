import sys
import numpy as np
import cv2

# --- PyQt5/6 Kompatibilität ---
try:
    from PyQt6 import QtCore, QtGui, QtWidgets
    QT6 = True
    AlignCenter = QtCore.Qt.AlignmentFlag.AlignCenter
    KeepAspectRatio = QtCore.Qt.AspectRatioMode.KeepAspectRatio
    SmoothTransformation = QtCore.Qt.TransformationMode.SmoothTransformation
    MouseButtonLeft = QtCore.Qt.MouseButton.LeftButton
except Exception:
    from PyQt5 import QtCore, QtGui, QtWidgets
    QT6 = False
    AlignCenter = QtCore.Qt.AlignCenter
    KeepAspectRatio = QtCore.Qt.KeepAspectRatio
    SmoothTransformation = QtCore.Qt.SmoothTransformation
    MouseButtonLeft = QtCore.Qt.LeftButton


# --- Klickbares Label für Bildanzeige ---
class ClickableImage(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(AlignCenter)
        self.setFixedSize(380, 300)
        self._img = None

    def set_cv_image(self, bgr_img):
        self._img = bgr_img
        self._update_pixmap()

    def _update_pixmap(self):
        if self._img is None:
            self.setPixmap(QtGui.QPixmap())
            return
        rgb = cv2.cvtColor(self._img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QtGui.QImage(rgb.data, w, h, rgb.strides[0],
                            QtGui.QImage.Format.Format_RGB888 if QT6 else QtGui.QImage.Format_RGB888)
        pm = QtGui.QPixmap.fromImage(qimg)
        self.setPixmap(pm.scaled(self.size(), KeepAspectRatio, SmoothTransformation))

    def mouseReleaseEvent(self, event):
        if self._img is None or event.button() != MouseButtonLeft:
            return super().mouseReleaseEvent(event)

        pm = self.pixmap()
        if pm is None:
            return super().mouseReleaseEvent(event)

        label_w = self.width()
        label_h = self.height()
        pm_w = pm.width()
        pm_h = pm.height()
        off_x = (label_w - pm_w) // 2
        off_y = (label_h - pm_h) // 2

        x = int(event.position().x() if QT6 else event.x())
        y = int(event.position().y() if QT6 else event.y())

        if not (off_x <= x < off_x + pm_w and off_y <= y < off_y + pm_h):
            return super().mouseReleaseEvent(event)

        img_h, img_w = self._img.shape[:2]
        scale = min(label_w / img_w, label_h / img_h)
        img_x = int((x - off_x) / scale)
        img_y = int((y - off_y) / scale)

        img_x = max(0, min(img_w - 1, img_x))
        img_y = max(0, min(img_h - 1, img_y))

        self.clicked.emit(img_x, img_y)


# --- Hauptklasse ---
class ColorPicker(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenCV HSV ColorPicker (feste Größe)")
        self.setFixedSize(1200, 700)  # Fenstergröße fixieren

        self.bgr_image = None
        self.hsv_image = None
        self.clicked_hsv = []

        self._build_ui()

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_views)
        self.timer.start()

    def _build_ui(self):
        main = QtWidgets.QVBoxLayout(self)
        main.setContentsMargins(10, 10, 10, 10)
        main.setSpacing(10)

        # --- Top-Leiste ---
        top_bar = QtWidgets.QHBoxLayout()
        self.btn_open = QtWidgets.QPushButton("Bild öffnen…")
        self.btn_set_from_clicks = QtWidgets.QPushButton("Grenzen aus Klicks setzen")
        self.btn_copy = QtWidgets.QPushButton("In Zwischenablage kopieren")
        self.btn_reset = QtWidgets.QPushButton("Zurücksetzen")

        for b in [self.btn_open, self.btn_set_from_clicks, self.btn_copy, self.btn_reset]:
            b.setFixedHeight(30)

        top_bar.addWidget(self.btn_open)
        top_bar.addSpacing(10)
        top_bar.addWidget(self.btn_set_from_clicks)
        top_bar.addWidget(self.btn_copy)
        top_bar.addStretch(1)
        top_bar.addWidget(self.btn_reset)
        main.addLayout(top_bar)

        # --- Bildbereiche ---
        views = QtWidgets.QHBoxLayout()
        self.view_input = ClickableImage()
        self.view_mask = QtWidgets.QLabel("Maske")
        self.view_mask.setAlignment(AlignCenter)
        self.view_mask.setFixedSize(380, 300)
        self.view_mask.setFrameShape(QtWidgets.QFrame.Shape.Box if QT6 else QtWidgets.QFrame.Box)

        self.view_result = QtWidgets.QLabel("Ergebnis")
        self.view_result.setAlignment(AlignCenter)
        self.view_result.setFixedSize(380, 300)
        self.view_result.setFrameShape(QtWidgets.QFrame.Shape.Box if QT6 else QtWidgets.QFrame.Box)

        views.addWidget(self.view_input)
        views.addWidget(self.view_mask)
        views.addWidget(self.view_result)
        main.addLayout(views)

        # --- Reglerbereich ---
        controls = QtWidgets.QGridLayout()

        def add_slider(row, label, minv, maxv, start):
            lbl = QtWidgets.QLabel(label)
            slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            slider.setRange(minv, maxv)
            slider.setValue(start)
            spin = QtWidgets.QSpinBox()
            spin.setRange(minv, maxv)
            spin.setValue(start)
            slider.valueChanged.connect(spin.setValue)
            spin.valueChanged.connect(slider.setValue)
            controls.addWidget(lbl, row, 0)
            controls.addWidget(slider, row, 1)
            controls.addWidget(spin, row, 2)
            return slider, spin

        self.s_min_h, self.sb_min_h = add_slider(0, "Min H", 0, 179, 0)
        self.s_min_s, self.sb_min_s = add_slider(1, "Min S", 0, 255, 0)
        self.s_min_v, self.sb_min_v = add_slider(2, "Min V", 0, 255, 0)
        self.s_max_h, self.sb_max_h = add_slider(3, "Max H", 0, 179, 179)
        self.s_max_s, self.sb_max_s = add_slider(4, "Max S", 0, 255, 255)
        self.s_max_v, self.sb_max_v = add_slider(5, "Max V", 0, 255, 255)

        controls.addWidget(QtWidgets.QLabel("Erode"), 0, 3)
        self.sb_erode = QtWidgets.QSpinBox()
        self.sb_erode.setRange(0, 10)
        self.sb_erode.setValue(2)
        controls.addWidget(self.sb_erode, 0, 4)

        controls.addWidget(QtWidgets.QLabel("Dilate"), 1, 3)
        self.sb_dilate = QtWidgets.QSpinBox()
        self.sb_dilate.setRange(0, 10)
        self.sb_dilate.setValue(2)
        controls.addWidget(self.sb_dilate, 1, 4)

        self.lbl_click_info = QtWidgets.QLabel("Geklickte HSV-Werte: 0")
        controls.addWidget(self.lbl_click_info, 2, 3, 1, 2)

        main.addLayout(controls)

        # Buttons verbinden
        self.btn_open.clicked.connect(self.open_image)
        self.btn_set_from_clicks.clicked.connect(self.apply_minmax_from_clicks)
        self.btn_copy.clicked.connect(self.copy_to_clipboard)
        self.btn_reset.clicked.connect(self.reset_all)
        self.view_input.clicked.connect(self.on_image_click)

    # ---------- Logik ----------
    def open_image(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Bild auswählen", "", "Bilder (*.png *.jpg *.jpeg *.bmp)")
        if not path:
            return
        img = cv2.imread(path)
        if img is None:
            QtWidgets.QMessageBox.warning(self, "Fehler", "Bild konnte nicht geladen werden.")
            return
        self.bgr_image = img
        self.hsv_image = cv2.cvtColor(self.bgr_image, cv2.COLOR_BGR2HSV)
        self.view_input.set_cv_image(self.bgr_image)

    def on_image_click(self, x, y):
        if self.hsv_image is None:
            return
        hsv_val = self.hsv_image[y, x].tolist()
        self.clicked_hsv.append(hsv_val)
        self.lbl_click_info.setText(f"Geklickte HSV-Werte: {len(self.clicked_hsv)}")

    def get_bounds(self):
        lower = np.array([self.sb_min_h.value(), self.sb_min_s.value(), self.sb_min_v.value()])
        upper = np.array([self.sb_max_h.value(), self.sb_max_s.value(), self.sb_max_v.value()])
        return lower, upper

    def update_views(self):
        if self.hsv_image is None:
            return
        lower, upper = self.get_bounds()
        mask = cv2.inRange(self.hsv_image, lower, upper)
        if self.sb_erode.value() > 0:
            mask = cv2.erode(mask, None, iterations=self.sb_erode.value())
        if self.sb_dilate.value() > 0:
            mask = cv2.dilate(mask, None, iterations=self.sb_dilate.value())
        result = cv2.bitwise_and(self.bgr_image, self.bgr_image, mask=mask)
        self._set_label_gray(self.view_mask, mask)
        self._set_label_bgr(self.view_result, result)

    def _set_label_bgr(self, label, img):
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        qimg = QtGui.QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0],
                            QtGui.QImage.Format.Format_RGB888 if QT6 else QtGui.QImage.Format_RGB888)
        pm = QtGui.QPixmap.fromImage(qimg)
        label.setPixmap(pm.scaled(label.size(), KeepAspectRatio, SmoothTransformation))

    def _set_label_gray(self, label, img):
        qimg = QtGui.QImage(img.data, img.shape[1], img.shape[0], img.strides[0],
                            QtGui.QImage.Format.Format_Grayscale8 if QT6 else QtGui.QImage.Format_Grayscale8)
        pm = QtGui.QPixmap.fromImage(qimg)
        label.setPixmap(pm.scaled(label.size(), KeepAspectRatio, SmoothTransformation))

    def apply_minmax_from_clicks(self):
        if not self.clicked_hsv:
            return
        arr = np.array(self.clicked_hsv)
        mins = arr.min(axis=0)
        maxs = arr.max(axis=0)
        self.sb_min_h.setValue(int(mins[0]))
        self.sb_min_s.setValue(int(mins[1]))
        self.sb_min_v.setValue(int(mins[2]))
        self.sb_max_h.setValue(int(maxs[0]))
        self.sb_max_s.setValue(int(maxs[1]))
        self.sb_max_v.setValue(int(maxs[2]))

    def copy_to_clipboard(self):
        lower, upper = self.get_bounds()
        text = f"lower = [{lower[0]}, {lower[1]}, {lower[2]}]\nupper = [{upper[0]}, {upper[1]}, {upper[2]}]"
        QtWidgets.QApplication.clipboard().setText(text)
        QtWidgets.QToolTip.showText(self.mapToGlobal(QtCore.QPoint(20, 20)), "Kopiert")

    def reset_all(self):
        self.clicked_hsv.clear()
        self.lbl_click_info.setText("Geklickte HSV-Werte: 0")
        self.sb_min_h.setValue(0)
        self.sb_min_s.setValue(0)
        self.sb_min_v.setValue(0)
        self.sb_max_h.setValue(179)
        self.sb_max_s.setValue(255)
        self.sb_max_v.setValue(255)
        self.sb_erode.setValue(2)
        self.sb_dilate.setValue(2)


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = ColorPicker()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
