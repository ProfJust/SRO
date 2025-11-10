# ChatGPT: erstelle mir ein PyQt6 Programm mit mehreren Buttons und Slidern
import sys
import random
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QSlider,
    QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QStatusBar
)


class ControlWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PyQt6 – Buttons & Slider Demo")
        self.setFixedSize(520, 380)  # feste Fenstergröße

        # ---- Settings (Werte zwischen Sessions speichern) ----
        self.settings = QSettings("OJ-Labs", "PyQt6ButtonsSliders")

        # ---- Zentrales Widget + Layouts ----
        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ---- Farb-Preview ----
        self.preview = QLabel()
        self.preview.setMinimumHeight(120)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet("border: 1px solid #aaa; border-radius: 8px;")
        root.addWidget(self.preview)

        # ---- Slider-Gruppe ----
        sliders_group = QGroupBox("Farbregler (RGB 0–255)")
        grid = QGridLayout(sliders_group)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        self.sl_r = self._make_slider()
        self.sl_g = self._make_slider()
        self.sl_b = self._make_slider()

        self.lbl_r = QLabel("R: 0")
        self.lbl_g = QLabel("G: 0")
        self.lbl_b = QLabel("B: 0")

        grid.addWidget(self._row("Rot", self.sl_r, self.lbl_r), 0, 0)
        grid.addWidget(self._row("Grün", self.sl_g, self.lbl_g), 1, 0)
        grid.addWidget(self._row("Blau", self.sl_b, self.lbl_b), 2, 0)

        root.addWidget(sliders_group)

        # ---- Button-Leiste ----
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_reset = QPushButton("Zurücksetzen")
        self.btn_random = QPushButton("Zufall")
        self.btn_lock = QPushButton("Sperren")
        self.btn_quit = QPushButton("Beenden")

        self.btn_reset.setToolTip("Alle Slider auf 0 setzen (Alt+R)")
        self.btn_random.setToolTip("Zufällige Farbe einstellen (Alt+Z)")
        self.btn_lock.setToolTip("Slider sperren/entsperren (Alt+S)")
        self.btn_quit.setToolTip("Programm beenden (Alt+B)")

        self.btn_reset.setShortcut("Alt+R")
        self.btn_random.setShortcut("Alt+Z")
        self.btn_lock.setShortcut("Alt+S")
        self.btn_quit.setShortcut("Alt+B")

        for b in (self.btn_reset, self.btn_random, self.btn_lock, self.btn_quit):
            b.setMinimumHeight(36)
            btn_row.addWidget(b)

        root.addLayout(btn_row)

        # ---- Statusleiste ----
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # ---- Signale verbinden ----
        self.sl_r.valueChanged.connect(self.on_value_changed)
        self.sl_g.valueChanged.connect(self.on_value_changed)
        self.sl_b.valueChanged.connect(self.on_value_changed)

        self.btn_reset.clicked.connect(self.on_reset)
        self.btn_random.clicked.connect(self.on_random)
        self.btn_lock.clicked.connect(self.on_lock_toggle)
        self.btn_quit.clicked.connect(self.close)

        # ---- Startwerte laden ----
        self._load_settings()
        self._apply_color_to_preview()
        self._update_labels()

    # ---------- Helpers ----------

    def _make_slider(self) -> QSlider:
        sl = QSlider(Qt.Orientation.Horizontal)
        sl.setRange(0, 255)
        sl.setSingleStep(1)
        sl.setPageStep(5)
        sl.setTickPosition(QSlider.TickPosition.TicksBelow)
        sl.setTickInterval(16)
        return sl

    def _row(self, title: str, slider: QSlider, value_label: QLabel) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)

        lbl = QLabel(title)
        lbl.setMinimumWidth(40)
        lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        value_label.setMinimumWidth(60)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        h.addWidget(lbl, 0)
        h.addWidget(slider, 1)
        h.addWidget(value_label, 0)
        return w

    def _apply_color_to_preview(self):
        r, g, b = self.sl_r.value(), self.sl_g.value(), self.sl_b.value()
        self.preview.setText(f"rgb({r}, {g}, {b})")
        self.preview.setStyleSheet(
            f"border: 1px solid #aaa; border-radius: 8px; "
            f"background-color: rgb({r}, {g}, {b}); color: {'black' if (r+g+b) > 380 else 'white'};"
        )

    def _update_labels(self):
        self.lbl_r.setText(f"R: {self.sl_r.value()}")
        self.lbl_g.setText(f"G: {self.sl_g.value()}")
        self.lbl_b.setText(f"B: {self.sl_b.value()}")

    def _save_settings(self):
        self.settings.setValue("r", self.sl_r.value())
        self.settings.setValue("g", self.sl_g.value())
        self.settings.setValue("b", self.sl_b.value())
        self.settings.setValue("locked", self._sliders_locked())

    def _load_settings(self):
        r = int(self.settings.value("r", 32))
        g = int(self.settings.value("g", 96))
        b = int(self.settings.value("b", 192))
        locked = self.settings.value("locked", False, type=bool)

        self.sl_r.setValue(r)
        self.sl_g.setValue(g)
        self.sl_b.setValue(b)

        self._set_sliders_locked(locked)
        self.btn_lock.setText("Entsperren" if locked else "Sperren")

    def _set_sliders_locked(self, locked: bool):
        for sl in (self.sl_r, self.sl_g, self.sl_b):
            sl.setEnabled(not locked)

    def _sliders_locked(self) -> bool:
        return not self.sl_r.isEnabled()

    # ---------- Slots ----------

    def on_value_changed(self, _=None):
        self._apply_color_to_preview()
        self._update_labels()
        self._save_settings()
        r, g, b = self.sl_r.value(), self.sl_g.value(), self.sl_b.value()
        self.status.showMessage(f"Farbe geändert: R={r} G={g} B={b}", 1500)

    def on_reset(self):
        self.sl_r.setValue(0)
        self.sl_g.setValue(0)
        self.sl_b.setValue(0)
        self.status.showMessage("Zurückgesetzt auf (0, 0, 0)", 1500)

    def on_random(self):
        self.sl_r.setValue(random.randint(0, 255))
        self.sl_g.setValue(random.randint(0, 255))
        self.sl_b.setValue(random.randint(0, 255))
        self.status.showMessage("Zufallswerte gesetzt", 1500)

    def on_lock_toggle(self):
        locked = not self._sliders_locked()
        self._set_sliders_locked(locked)
        self.btn_lock.setText("Entsperren" if locked else "Sperren")
        self.status.showMessage("Slider gesperrt" if locked else "Slider entsperrt", 1500)
        self._save_settings()

    # ---------- Standard-Verhalten überschreiben ----------

    def closeEvent(self, event):
        self._save_settings()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    win = ControlWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
