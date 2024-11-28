#!/usr/bin/env python3
# pyQt6_10_PixDynamic.py
#---------------------------------------
# Erstellt ein Fenster einem bewegten Streichholz
# -----------------------------------------
# last edited by OJ am 26.11.2024 
#
# Usage: 
# in der Windows-Power-Shell in das VErzeichnis springen und
# > cd 'C:\Users\RoboAdmin\mySciebo\_SRO\_GitHub_LaborPC\SRO\Py_Qt6\'
# ausführen
# > python .\pyQt6_10_Pixmap.py
#
# Hier aus dem Debugger funktioniert es nicht (Fenster ohne alles)
# Die Bilddateie muss im selben Ordner liegen !!

import sys
from PyQt6.QtCore import (Qt, QTimer)
from PyQt6.QtWidgets import (QWidget, QPushButton, QApplication, QLabel)
from PyQt6.QtGui import QPixmap
WINDOWS_BREITE=1000

class Ui(QWidget):
    
    #statische Klassenvariablen
    pos_label_x = 20
    
    def __init__(self): #Konstrukor
        #Konstruktor der Elternklasse aufrufen
        super(Ui, self).__init__()  
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)  
        self.timer.start(100)        
        self.initUI()
    
    def initUI(self):         
        self.lbl = QLabel(" Ein Label ", self)
        self.lbl.setGeometry(20, 20,  196, 442)
        #self.lbl.setStyleSheet("background-color: blue")
        
        pix = QPixmap("Streicholz.png") #196x442 Pixel
        self.lbl.setPixmap(pix)
            
        #UI-Fenster Konfigurieren
        self.setGeometry(20, 20,  WINDOWS_BREITE, 500)
        self.setWindowTitle('Qt - Pixmap')
        self.show()
        
    def update(self): 
        self.pos_label_x = self.pos_label_x+10
        if self.pos_label_x > WINDOWS_BREITE:
            self.pos_label_x = 0
        self.lbl.move(self.pos_label_x,20)
    
if __name__ == '__main__':    
    app = QApplication(sys.argv)
    ui = Ui()
    sys.exit(app.exec())