# pyQt6_01_firtsTest.py
#---------------------------------------
# Erstellt ein erstes Fenster mit PyQt6
# -----------------------------------------
# OJ am 22.11.2024 
# ggf. pip install PyQt6

# 1. Importieren der benötigten Module
from PyQt6.QtWidgets import QApplication, QWidget, QLabel

# Wird benötigt, um Kommandozeilenargumente an die Anwendung weiterzugeben
import sys

# --- Ausgabefunktion für das GUI ----------
def window():
   # QApplication: Verwaltet die Anwendung und deren Ereignisschleife
   app = QApplication(sys.argv) # Erstellt eine Instanz von QApplication

   # Erstellen des Fensters
   # QWidget: Basis-Klasse für alle GUI-Elemente, hier das Hauptfenster.
   w = QWidget() # Instanz von QWidget erstellen
   # Set Size and Title of Window
   # Legt die Position (x=100, y=100) und die Größe (Breite=200, Höhe=50) des Fensters fest.
   w.setGeometry(100,100,200,50) # x, y, w, h
   w.setWindowTitle("PyQt - Version Qt6")

   # QLabel: Ein Widget, das Text oder Bilder anzeigen kann
   label = QLabel(w)
   label.setText("Hello World!")  
   # Positioniert das Label innerhalb des Fensters bei (x=50, y=20).
   label.move(50, 20)
  
   # Fenster anzeigen (Windows are hidden by default)
   w.show()
   #  Ereignisschleife starten
   app.exec()
   
# If Stellt sicher, dass window() nur aufgerufen wird, 
# wenn das Skript direkt ausgeführt wird und nicht beim Import als Modul.   
if __name__ == '__main__':
   window()




