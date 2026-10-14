from PyQt6.QtWidgets import QApplication, QWidget, QTabWidget, QVBoxLayout, QLabel
import sys

app = QApplication(sys.argv)

main_window = QWidget()
main_window.setWindowTitle('PyQt QTabWidget Demo')
layout = QVBoxLayout(main_window)

tab_widget = QTabWidget()

# Tab 1
tab1 = QWidget()
tab1_layout = QVBoxLayout(tab1)
tab1_layout.addWidget(QLabel("Inhalt Tab 1"))
tab_widget.addTab(tab1, "Tab 1")

# Tab 2
tab2 = QWidget()
tab2_layout = QVBoxLayout(tab2)
tab2_layout.addWidget(QLabel("Inhalt Tab 2"))
tab_widget.addTab(tab2, "Tab 2")

layout.addWidget(tab_widget)
main_window.setLayout(layout)
main_window.show()
app.exec()
