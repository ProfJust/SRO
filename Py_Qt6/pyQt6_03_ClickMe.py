import sys
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWidgets import QPushButton
#------------------------------------------------------------------------
# pyQt6_03_ClickMe.py
# Beispiel fuer Push_Button mit Click-Event
# 26.11.2024 by OJ
#------------------------------------------------------------------------
from PyQt6.QtCore import QSize    

class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        self.setMinimumSize(QSize(300, 200))    
        self.setWindowTitle("PyQt button example - pythonprogramminglanguage.com")

        self.pybutton = QPushButton('Click me', self)
        self.pybutton.resize(100,32)
        self.pybutton.move(50, 50)     
        # Signal mit Slot verbinden
        self.pybutton.clicked.connect(self.clickSlot)          

    def clickSlot(self):
        print('Clicked Pyqt button.')

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit( app.exec() )
