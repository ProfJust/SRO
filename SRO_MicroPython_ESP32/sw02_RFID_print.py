import serial

PORT = "COM17"          # anpassen: z.B. "COM4" oder "/dev/ttyUSB0"
BAUDRATE = 115200      # wie beim ESP32/MicroPython

def main():
    with serial.Serial(PORT, BAUDRATE, timeout=1) as ser:
        print(f"Geöffnet: {ser.portstr}")
        print("Warte auf Daten ... (Strg+C zum Abbrechen)")
        while True:
            line = ser.readline()  # liest bis '\n' oder timeout
            if not line:
                continue           # nichts empfangen
            try:
                text = line.decode("utf-8", errors="ignore").strip()
            except UnicodeDecodeError:
                continue
            if text:
                print(text)

if __name__ == "__main__":
    main()
