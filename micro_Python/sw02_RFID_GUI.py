import sys
import re

from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtSerialPort import QSerialPort
from PyQt6.QtCore import QIODevice, pyqtSignal, QObject


class SerialReader(QObject):
    tag_received = pyqtSignal(str)

    def __init__(self, port_name: str, baudrate: int = 115200, parent=None):
        super().__init__(parent)
        self.serial = QSerialPort(self)
        self.serial.setPortName(port_name)  # z.B. "COM4" oder "/dev/ttyUSB0"
        self.serial.setBaudRate(baudrate)
        self.serial.readyRead.connect(self._on_ready_read)
        self.buffer = b""

        if not self.serial.open(QIODevice.OpenModeFlag.ReadOnly):
            print(f"Konnte Port {port_name} nicht öffnen")

        # Regex für Zeilen wie: "#RFID:  0xA1B2C3D4"
        self._pattern = re.compile(r"#RFID:\s*(\S+)")

    def _on_ready_read(self):
        # alles Neue lesen und in einen Python-bytes-Puffer hängen
        data = bytes(self.serial.readAll())
        self.buffer += data

        # Zeilenweise verarbeiten
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            text = line.decode(errors="ignore").strip()
            self._process_line(text)

    def _process_line(self, text: str):
        match = self._pattern.search(text)
        if match:
            uid = match.group(1)
            self.tag_received.emit(uid)


class MainWindow(QMainWindow):
    def __init__(self, port_name: str):
        super().__init__()

        self.setWindowTitle("RFID-Viewer")

        self.label_last = QLabel("Letzter RFID-Tag: (noch keiner)")
        self.label_raw = QLabel("Letzte Zeile vom ESP32:")

        layout = QVBoxLayout()
        layout.addWidget(self.label_last)
        layout.addWidget(self.label_raw)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.reader = SerialReader(port_name)
        self.reader.tag_received.connect(self.on_tag_received)

    def on_tag_received(self, uid: str):
        self.label_last.setText(f"Letzter RFID-Tag: {uid}")
        self.label_raw.setText(f"Letzte Zeile vom ESP32: #RFID: {uid}")


def main():
    # Port hier anpassen
    port_name = "COM4"  # Windows: z.B. "COM4"; Linux: "/dev/ttyUSB0" oder "/dev/ttyACM0"

    app = QApplication(sys.argv)
    win = MainWindow(port_name)
    win.resize(400, 120)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
