#!/usr/bin/env python3
# pyQt6_11_PixDynamic_Ball_vor_Gras.py
#---------------------------------------
# Erstellt ein Fenster mit Gras vor dem ein Ball fliegt
# -----------------------------------------
# last edited by OJ am 26.11.2024 
#
# Usage: 
# in der Windows-Power-Shell in das VErzeichnis springen und
# > cd 'C:\Users\RoboAdmin\mySciebo\_SRO\_GitHub_LaborPC\SRO\Py_Qt6\'
# ausführen
# > python .\pyQt6_11_PixDynamic_Ball_vor_Gras.py
#
# Hier aus dem Debugger funktioniert es nicht (Fenster ohen Gras und ohne Ball)
# Die Bilddateien müssen im selben Ordner liegen !!

import sys
from PyQt6.QtCore import (Qt, QTimer, QRect)
from PyQt6.QtWidgets import (QWidget, QPushButton, QApplication, QLabel)
from PyQt6.QtGui import QPainter, QColor, QFont
from PyQt6.QtGui import QPixmap


class Ui(QWidget):
    # statische Klassenvariablen
    pos_x = 200
    pos_y = 20
    speed_x = -10
    speed_y = +12

    def __init__(self):  # Konstrukor
        # Konstruktor der Elternklasse aufrufen
        super(Ui, self).__init__()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(20)
        self.initUI()

    def initUI(self):
        # UI-Fenster Konfigurieren
        self.setGeometry(30, 30, 600, 600)
        self.setWindowTitle('Qt - Painter')
        self.show()

    def paintEvent(self, event):
        p = QPainter()
        p.begin(self)
        self.drawFunc(event, p)
        p.end()

    def drawFunc(self, event, p):
        # Hintergrund mit Pixmap
        pix = QPixmap("gras.jpg")
        p.drawPixmap(self.rect(), pix)

        # bewegtes Rechteck zeichnen mit Pixmap
        pix2 = QPixmap("ball_transparent.png")  # PNG mit Transparenz
        target = QRect(self.pos_x, self.pos_y, 50, 50)  # import QRect
        p.drawPixmap(target, pix2)

    def update(self):
        self.pos_x = self.pos_x + self.speed_x
        self.pos_y = self.pos_y + self.speed_y
        # Pruefe Rand
        if self.pos_x < 0:
            self.speed_x = -self.speed_x
        if self.pos_x > 600:
            self.speed_x = -self.speed_x
        if self.pos_y < 0:
            self.speed_y = -self.speed_y
        if self.pos_y > 600:
            self.speed_y = -self.speed_y
        self.repaint()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ui = Ui()
    sys.exit(app.exec())
