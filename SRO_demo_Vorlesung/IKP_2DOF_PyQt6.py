"""Inverse Kinematik eines ebenen 2R-Roboters mit PyQt6.
Installation: python -m pip install PyQt6
Start: python IKP_2DOF_PyQt6.py
"""
import math
import sys
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QPainter, QPen, QFont
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel,
                             QSlider, QPushButton, QHBoxLayout, QVBoxLayout,
                             QGroupBox)

L1 = 150.0  # mm
L2 = 110.0  # mm


def inverse_kinematik(x, y, ellbogen_oben=True):
    """Berechnet Gelenkwinkel (Grad) oder None bei unerreichbarem Ziel."""
    c2 = (x*x + y*y - L1*L1 - L2*L2) / (2*L1*L2)
    if c2 < -1.0 - 1e-9 or c2 > 1.0 + 1e-9:
        return None
    c2 = max(-1.0, min(1.0, c2))
    theta2 = math.acos(c2) * (1 if ellbogen_oben else -1)
    theta1 = math.atan2(y, x) - math.atan2(L2*math.sin(theta2),
                                           L1 + L2*math.cos(theta2))
    return math.degrees(theta1), math.degrees(theta2)


def vorwaertskinematik(t1, t2):
    a, b = math.radians(t1), math.radians(t1+t2)
    x1, y1 = L1*math.cos(a), L1*math.sin(a)
    return x1, y1, x1 + L2*math.cos(b), y1 + L2*math.sin(b)


class RoboterAnsicht(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(480, 480)
        self.x, self.y = 180, 100
        self.winkel = inverse_kinematik(self.x, self.y, True)

    def set_zustand(self, x, y, winkel):
        self.x, self.y, self.winkel = x, y, winkel
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor('white'))
        w, h = self.width(), self.height()
        scale = min((w-80)/(2*(L1+L2)), (h-80)/(2*(L1+L2)))
        cx, cy = w/2, h/2
        def pt(x, y):
            return QPointF(cx+x*scale, cy-y*scale)

        p.setPen(QPen(QColor('#d5dde7'), 1))
        p.drawLine(QPointF(12,cy), QPointF(w-12,cy))
        p.drawLine(QPointF(cx,12), QPointF(cx,h-12))
        p.setPen(QPen(QColor('#64748b'), 1))
        p.drawText(int(w-30), int(cy-8), 'X')
        p.drawText(int(cx+8), 20, 'Y')
        p.setPen(QPen(QColor('#a6c9e2'), 1.5, Qt.PenStyle.DashLine))
        for r in (L1+L2, abs(L1-L2)):
            p.drawEllipse(pt(0,0), r*scale, r*scale)

        # Ziel bleibt sichtbar, auch wenn es außerhalb des Arbeitsraums liegt.
        p.setPen(QPen(QColor('#d21d35'), 2))
        p.setBrush(QColor('#f8c5cd'))
        p.drawEllipse(pt(self.x,self.y), 5, 5)
        p.drawText(pt(self.x,self.y)+QPointF(10,-10), 'Ziel')

        if self.winkel is not None:
            x1,y1,x2,y2 = vorwaertskinematik(*self.winkel)
            p.setPen(QPen(QColor('#2584bc'), 11, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap))
            p.drawLine(pt(0,0),pt(x1,y1))
            p.setPen(QPen(QColor('#f28b30'), 10, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap))
            p.drawLine(pt(x1,y1),pt(x2,y2))
            for a,b in ((0,0),(x1,y1)):
                p.setPen(QPen(QColor('#1e3a5f'),2))
                p.setBrush(QColor('#e8f3fb'))
                p.drawEllipse(pt(a,b),8,8)
            p.setPen(QPen(QColor('#ba2433'),2))
            p.setBrush(QColor('#ef4444'))
            p.drawEllipse(pt(x2,y2),6,6)
            p.setFont(QFont('Arial',10))
            p.drawText(pt(x2,y2)+QPointF(10,18),'TCP')
            # Gelenkwinkel direkt an den Gelenken in Grad anzeigen
            t1, t2 = self.winkel
            p.setPen(QPen(QColor('#164b75'), 1))
            p.drawText(pt(0,0)+QPointF(12,-14), f'θ₁ = {t1:.1f}°')
            p.drawText(pt(x1,y1)+QPointF(12,-14), f'θ₂ = {t2:.1f}°')
        p.setPen(QPen(QColor('#334155'),1))
        p.drawText(12,h-12,'Blau: L1 = 150 mm     Orange: L2 = 110 mm')
        p.end()


class Fenster(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('IKP – Inverse Kinematik eines 2-DOF-Roboters')
        self.ellbogen_oben = True
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        controls = QVBoxLayout()
        layout.addLayout(controls,1)
        self.ansicht = RoboterAnsicht()
        layout.addWidget(self.ansicht,2)

        titel = QLabel('Inverse Kinematik (IKP)')
        titel.setStyleSheet('font-size: 20px; font-weight: bold; color: #164b75;')
        controls.addWidget(titel)
        controls.addWidget(QLabel('Gegeben: TCP-Zielposition (X, Y)\nGesucht: Gelenkwinkel θ₁ und θ₂'))

        self.x_slider, self.x_label = self._slider(controls, 'X-Position', -260,260,180)
        self.y_slider, self.y_label = self._slider(controls, 'Y-Position', -260,260,100)
        group = QGroupBox('Inverse Kinematik: zwei Konfigurationen')
        gb = QVBoxLayout(group)
        self.btn_oben = QPushButton('Lösung 1 – Ellbogen oben (θ₂ > 0)')
        self.btn_unten = QPushButton('Lösung 2 – Ellbogen unten (θ₂ < 0)')
        gb.addWidget(self.btn_oben)
        gb.addWidget(self.btn_unten)
        controls.addWidget(group)
        self.info = QLabel()
        self.info.setWordWrap(True)
        self.info.setStyleSheet('font-size: 14px; padding: 10px; background: #edf5fc;')
        controls.addWidget(self.info)
        self.winkel_label = QLabel()
        self.winkel_label.setStyleSheet(
            'font-size: 18px; font-weight: bold; color: #164b75; '
            'padding: 12px; background: #dceeff; border-radius: 6px;'
        )
        controls.addWidget(self.winkel_label)
        reset = QPushButton('Startposition (X = 180, Y = 100)')
        controls.addWidget(reset)
        controls.addStretch()
        self.x_slider.valueChanged.connect(self.aktualisieren)
        self.y_slider.valueChanged.connect(self.aktualisieren)
        self.btn_oben.clicked.connect(lambda: self.waehle(True))
        self.btn_unten.clicked.connect(lambda: self.waehle(False))
        reset.clicked.connect(self.reset)
        self.aktualisieren()
        self.resize(1040,570)

    def _slider(self, layout, name, lo, hi, value):
        group = QGroupBox(name)
        v = QVBoxLayout(group)
        label = QLabel()
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(lo,hi)
        slider.setValue(value)
        v.addWidget(label)
        v.addWidget(slider)
        layout.addWidget(group)
        return slider,label

    def waehle(self, oben):
        self.ellbogen_oben = oben
        self.aktualisieren()

    def reset(self):
        self.x_slider.setValue(180)
        self.y_slider.setValue(100)
        self.waehle(True)

    def aktualisieren(self):
        x, y = self.x_slider.value(), self.y_slider.value()
        self.x_label.setText(f'X = {x} mm')
        self.y_label.setText(f'Y = {y} mm')
        winkel = inverse_kinematik(x,y,self.ellbogen_oben)
        self.ansicht.set_zustand(x,y,winkel)
        self.btn_oben.setStyleSheet('background: #cce9ff;' if self.ellbogen_oben else '')
        self.btn_unten.setStyleSheet('background: #cce9ff;' if not self.ellbogen_oben else '')
        if winkel is None:
            self.winkel_label.setText('Gelenkwinkel: keine IK-Lösung')
            self.info.setText(f'Ziel ({x}, {y}) mm NICHT ERREICHBAR!\n'
                              f'Erlaubter Radius: {abs(L1-L2):.0f} bis {L1+L2:.0f} mm.\n'
                              'Der Roboter wird nicht gezeichnet.')
        else:
            t1,t2 = winkel
            self.winkel_label.setText(f'θ₁ = {t1:.2f}°     θ₂ = {t2:.2f}°')
            self.info.setText(f'TCP-Ziel: X = {x} mm, Y = {y} mm\n'
                              f'θ₁ = {t1:.2f}°\nθ₂ = {t2:.2f}°\n'
                              f'Konfiguration: {"Ellbogen oben" if self.ellbogen_oben else "Ellbogen unten"}\n'
                              f'TCP-Orientierung: {t1+t2:.2f}°')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    fenster = Fenster()
    fenster.show()
    sys.exit(app.exec())
