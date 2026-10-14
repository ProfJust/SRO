# pyQt6_02_hello_world_class.py
# Hello World im OO-Style
# ------------------------------------------------------------------
import sys
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtWidgets import QMainWindow, QLabel, QGridLayout, QWidget
from PyQt6.QtCore import QSize    


# Erstellt eine eigene Fensterklasse, die von QMainWindow erbt.
class HelloWindow(QMainWindow):
    # Im Konstruktor (__init__) wird das Hauptfenster initialisiert.
    def __init__(self):
        QMainWindow.__init__(self)

        self.setMinimumSize(QSize(240, 80))    
        self.setWindowTitle("WHS - Campus Bocholt")

        # Ein QMainWindow benötigt ein zentrales Widget (centralWidget),
        # das alle anderen Widgets enthält.
        centralWidget = QWidget(self)          
        self.setCentralWidget(centralWidget)   

        # Ein Gitter-Layout (QGridLayout) wird erstellt und dem zentralen Widget 
        # zugewiesen. Damit lassen sich Widgets flexibel anordnen.
        gridLayout = QGridLayout(self)     
        centralWidget.setLayout(gridLayout)  

        # Ein QLabel mit dem Text "Hello World from PyQt6" wird erzeugt.
        title = QLabel("Hello World from PyQt6", self)
        # Mit setAlignment(...) wird der Text im Label zentriert.
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        # Das Label wird im Layout an Position (0, 0) eingefügt (erste Zeile, erste Spalte).
        gridLayout.addWidget(title, 0, 0)


# If prüft, ob das Skript direkt ausgeführt wird.
if __name__ == "__main__": 
    # Erstellt die QApplication (Pflicht für jede PyQt-Anwendung).
    app = QtWidgets.QApplication(sys.argv)
    # Erstellt eine Instanz von HelloWindow und zeigt sie an.
    mainWin = HelloWindow()
    mainWin.show()
    # Startet die Ereignisschleife mit app.exec().
    sys.exit(app.exec())
    # Mit sys.exit(...) wird sichergestellt, dass das Programm sauber beendet wird.
