"""Direkte Kinematik eines ebenen 2R-Roboters – PyQt6.
Installation: python -m pip install PyQt6
Start: python DKP_2DOF_PyQt6.py
"""
import math
import sys
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (QApplication, QGroupBox, QHBoxLayout, QLabel,
                             QMainWindow, QPushButton, QSlider, QVBoxLayout,
                             QWidget)

L1 = 150.0  # mm
L2 = 110.0  # mm


def vorwaertskinematik(theta1_grad, theta2_grad):
    """Gelenkposition und TCP (mm), theta2 relativ zu Arm 1."""
    a = math.radians(theta1_grad)
    b = math.radians(theta1_grad + theta2_grad)
    x1, y1 = L1 * math.cos(a), L1 * math.sin(a)
    x2, y2 = x1 + L2 * math.cos(b), y1 + L2 * math.sin(b)
    return x1, y1, x2, y2


class RoboterAnsicht(QWidget):
    def __init__(self):
        super().__init__()
        self.theta1 = 35
        self.theta2 = 55
        self.setMinimumSize(460, 440)

    def set_winkel(self, t1, t2):
        self.theta1, self.theta2 = t1, t2
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor('#ffffff'))
        w, h = self.width(), self.height()
        massstab = min((w - 90) / (2 * (L1 + L2)), (h - 90) / (2 * (L1 + L2)))
        cx, cy = w / 2, h / 2

        def p(x, y):
            return QPointF(cx + x * massstab, cy - y * massstab)

        # Koordinatenachsen
        painter.setPen(QPen(QColor('#d2dbe5'), 1.5))
        painter.drawLine(QPointF(20, cy), QPointF(w - 20, cy))
        painter.drawLine(QPointF(cx, 20), QPointF(cx, h - 20))
        painter.setPen(QPen(QColor('#64748b'), 1))
        painter.drawText(int(w - 35), int(cy - 9), 'X')
        painter.drawText(int(cx + 9), 25, 'Y')

        # Maximaler Arbeitsraum: Kreisring, hier äußere und innere Grenze
        painter.setPen(QPen(QColor('#b8d9ec'), 1, Qt.PenStyle.DashLine))
        for radius in (L1 + L2, abs(L1 - L2)):
            r = radius * massstab
            painter.drawEllipse(p(0, 0), r, r)

        x1, y1, x2, y2 = vorwaertskinematik(self.theta1, self.theta2)
        painter.setPen(QPen(QColor('#2286c3'), 10, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap))
        painter.drawLine(p(0, 0), p(x1, y1))
        painter.setPen(QPen(QColor('#f08b2f'), 9, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap))
        painter.drawLine(p(x1, y1), p(x2, y2))

        for x, y in ((0, 0), (x1, y1)):
            painter.setPen(QPen(QColor('#1e3a5f'), 2))
            painter.setBrush(QColor('#e6f2fb'))
            painter.drawEllipse(p(x, y), 8, 8)

        painter.setPen(QPen(QColor('#b91c1c'), 2))
        painter.setBrush(QColor('#ef4444'))
        painter.drawEllipse(p(x2, y2), 6, 6)
        painter.setFont(QFont('Arial', 10))
        painter.drawText(p(x2, y2) + QPointF(12, -10), 'TCP')
        painter.setPen(QPen(QColor('#334155'), 1))
        painter.drawText(12, h - 14, 'Blau: L1 = 150 mm    Orange: L2 = 110 mm')


class Hauptfenster(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Direkte Kinematik (DKP) – 2-DOF-Roboter')
        self.resize(950, 540)
        haupt = QWidget()
        self.setCentralWidget(haupt)
        layout = QHBoxLayout(haupt)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(18)

        gruppe = QGroupBox('Gelenkwinkel einstellen')
        links = QVBoxLayout(gruppe)
        self.schieber = []
        self.wertelabel = []
        for nummer, start in ((1, 35), (2, 55)):
            beschriftung = QLabel()
            beschriftung.setStyleSheet('font-weight: bold; font-size: 15px;')
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(-180, 180)
            slider.setTickInterval(30)
            slider.setTickPosition(QSlider.TickPosition.TicksBelow)
            slider.setValue(start)
            slider.valueChanged.connect(self.aktualisieren)
            links.addWidget(beschriftung)
            links.addWidget(slider)
            links.addSpacing(20)
            self.schieber.append(slider)
            self.wertelabel.append(beschriftung)

        self.ergebnis = QLabel()
        self.ergebnis.setStyleSheet('font-size: 15px; background: #eaf4fc; padding: 14px;')
        links.addWidget(QLabel('Ergebnis der Vorwärtskinematik:'))
        links.addWidget(self.ergebnis)
        zurueck = QPushButton('Winkel zurücksetzen')
        zurueck.clicked.connect(self.zuruecksetzen)
        links.addWidget(zurueck)
        links.addStretch()
        layout.addWidget(gruppe, 1)

        self.ansicht = RoboterAnsicht()
        layout.addWidget(self.ansicht, 2)
        self.aktualisieren()

    def zuruecksetzen(self):
        self.schieber[0].setValue(35)
        self.schieber[1].setValue(55)

    def aktualisieren(self):
        t1, t2 = (s.value() for s in self.schieber)
        self.wertelabel[0].setText(f'Gelenk 1: θ₁ = {t1}°')
        self.wertelabel[1].setText(f'Gelenk 2: θ₂ = {t2}° (relativ)')
        _, _, x, y = vorwaertskinematik(t1, t2)
        self.ergebnis.setText(f'X = {x:.1f} mm\nY = {y:.1f} mm\n'
                              f'Orientierung = {t1 + t2}°')
        self.ansicht.set_winkel(t1, t2)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    fenster = Hauptfenster()
    fenster.show()
    sys.exit(app.exec())
