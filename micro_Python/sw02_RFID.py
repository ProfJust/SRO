# Micro PYthon Skript für den ESP32 und das RFDI Modul RC522
# -------------------------------------------------------------
# Verdrahtung:
# Signal 	GPIO ESP32 	Note
#   sck 	18 	
#   mosi 	23 	
#   miso 	19 	
#   cs 	5 	Labeled SDA on most RFID-RC522 boards
# -------------------------------------------------------------

# https://raw.githubusercontent.com/Tasm-Devil/micropython-mfrc522-esp32/refs/heads/master/examples/read.py

from time import sleep_ms
from machine import Pin, SoftSPI
from lib.rfid.mfrc522 import MFRC522



sck = Pin(18, Pin.OUT)
mosi = Pin(23, Pin.OUT)
miso = Pin(19, Pin.OUT)
spi = SoftSPI(
    baudrate=100000,
    polarity=0,
    phase=0,
    sck=sck,
    mosi=mosi,
    miso=miso,
)
sda = Pin(5, Pin.OUT)

def do_read():
    try:
        print("Los geht's")
        while True:
            rdr = MFRC522(spi, sda)
            uid = ""
            (stat, tag_type) = rdr.request(rdr.REQIDL)
            if stat == rdr.OK:
                (stat, raw_uid) = rdr.anticoll()
                if stat == rdr.OK:
                    uid = ("0x%02x%02x%02x%02x" % (raw_uid[0],
                                                   raw_uid[1],
                                                   raw_uid[2],
                                                   raw_uid[3]))
                    print("#RFID: ", uid)
                    sleep_ms(100)
    except KeyboardInterrupt:
        print("Bye")


if __name__ == "__main__":
    do_read()


    """
Besorge/bestätige das Modul:

Lade das passende mfrc522.py aus dem verwendeten Repo (z.B. Tasm‑Devil micropython-mfrc522-esp32).
​

Erzeuge die Verzeichnisstruktur lokal:

In deinem Projektordner:
lib/rfid/mfrc522.py

Kopiere die Dateien auf den ESP32 (Beispiel PowerShell):

powershell
mpremote connect COM4 mkdir :lib
mpremote connect COM4 mkdir :lib/rfid
mpremote connect COM4 cp .\lib\rfid\mfrc522.py :lib/rfid/mfrc522.py
mpremote connect COM4 cp .\sw02_RFID.py :main.py      # oder :sw02_RFID.py


"""