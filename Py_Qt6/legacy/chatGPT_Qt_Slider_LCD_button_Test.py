import sys
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QLabel,
)
from PyQt6.QtCore import Qt


class SliderWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PyQt6 Slider Steuerung")
        self.setGeometry(100, 100, 400, 200)

        # Label
        self.label = QLabel("Sliderwert: 50")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setValue(50)

        # Buttons
        self.button_minus = QPushButton("← Kleiner")
        self.button_plus = QPushButton("Größer →")

        # Signale verbinden
        self.button_minus.clicked.connect(self.slider_kleiner)
        self.button_plus.clicked.connect(self.slider_groesser)
        self.slider.valueChanged.connect(self.update_label)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.slider)
        layout.addWidget(self.button_minus)
        layout.addWidget(self.button_plus)

        self.setLayout(layout)

    def slider_kleiner(self):
        wert = self.slider.value()
        self.slider.setValue(wert - 10)

    def slider_groesser(self):
        wert = self.slider.value()
        self.slider.setValue(wert + 10)

    def update_label(self):
        self.label.setText(f"Sliderwert: {self.slider.value()}")


app = QApplication(sys.argv)

window = SliderWindow()
window.show()

sys.exit(app.exec())