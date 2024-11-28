#!/usr/bin/python3
# pyQt6_12_mouse_event.py
#---------------------------------------
# Erstellt ein Fenster einem bewegten Streichholz
# -----------------------------------------
# last edited by OJ am 26.11.2024 
#
# Usage: 
# in der Windows-Power-Shell in das VErzeichnis springen und
# > cd 'C:\Users\RoboAdmin\mySciebo\_SRO\_GitHub_LaborPC\SRO\Py_Qt6\'
# ausführen
# > python .\pyQt6_12_mouse_event.py
#
# Hier aus dem Debugger funktioniert es nicht (Fenster ohne alles)
# Die Bilddateie muss im selben Ordner liegen !!

# https://www.pythonguis.com/tutorials/pyqt6-signals-slots-events/#mouse-events


import sys
from PyQt6.QtCore import (Qt, QTimer, QRect)
from PyQt6.QtWidgets import (QWidget, QPushButton, QApplication, QLabel)
from PyQt6.QtGui import QPainter, QColor, QFont
from PyQt6.QtGui import QPixmap, QKeyEvent, QMouseEvent

class Ui(QWidget):
    #statische Klassenvariablen
    mouse_pos_x = 0
    mouse_pos_y = 0
        
    def __init__(self): #Konstrukor
        #Konstruktor der Elternklasse aufrufen
        super(Ui, self).__init__()  
        self.initUI()
    
    def initUI(self):         
        #UI-Fenster Konfigurieren
        self.setGeometry(30, 30, 600, 600)
        self.setWindowTitle('Qt - Mouse Event')
        self.setMouseTracking(True)
        self.show()
    
    def mousePressEvent(self, event): #Methode der QWidget-Klasse
        if  event.button()== Qt.MouseButton.LeftButton:
            print('Linksklick')
        if  event.button()== Qt.MouseButton.RightButton:
            print("Rechtsklick")
            
    def mouseDoubleClickEvent(self, event): #Methode der QWidget-Klasse
        if  event.button()== Qt.MouseButton.LeftButton:
            print('Linksklick doppelt, mit Rechtsklick doppelt wird es wieder klein')
            #self.showMaximized() #mit Titelzeile
            self.showFullScreen() #ohne Titelzeile
        if  event.button()== Qt.MouseButton.RightButton:
            print("Rechtsklick doppelt")
            self.showNormal() #urspruengiche Groesse
            #self.showMinimized() #ganz weg
            
    def paintEvent(self, event): #Methode der QWidget-Klasse
        p = QPainter()
        p.begin(self)
        self.drawFunc(event, p)        
        p.end()
    
    def mouseMoveEvent(self, event): #Methode der QWidget-Klasse
        self.mouse_pos_x = event.position().x()
        self.mouse_pos_y = event.position().y()
        #print Mouse Position
        print('x: %d  y: %d' % (self.mouse_pos_x, self.mouse_pos_y))

    def keyPressEvent(self, event): #Methode der QWidget-Klasse
        #if e.key() == Qt.Key.Key_Escape.value:
        if event.key() == Qt.Key.Key_Left:
            self.keyLeft = True
            print(' Key Left pressed')
        if event.key() == Qt.Key.Key_Right:
            self.keyRight = True
            print(' Key Right pressed')
            
    def keyReleaseEvent(self, event): #Methode der QWidget-Klasse
        if event.key() == Qt.Key.Key_Left:
             self.keyLeft = False
             print(' Key Left released ')
        if event.key() == Qt.Key.Key_Right:
             self.keyRight = False
             print(' Key Right released')
        event.accept()
    
    def drawFunc(self, event, p):            
        #Hintergrund mit Pixmap        
        pix = QPixmap("gras.jpg") 
        p.drawPixmap(self.rect(),pix)   
             
        
  
if __name__ == '__main__':    
    app = QApplication(sys.argv)
    ui = Ui()
    sys.exit(app.exec())
