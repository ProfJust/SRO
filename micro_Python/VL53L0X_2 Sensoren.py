"""
Docstring for VL53L0X_2 Sensoren
Hier ist die MicroPython-Version für den ESP32 mit 2× VL53L0X über XSHUT-Adressvergabe.

Sie benötigen zusätzlich eine MicroPython-Datei vl53l0x.py auf dem ESP32, z. B. den üblichen VL53L0X-MicroPython-Treiber.
"""
# Erster Test mit 2 Sensoren VL53L0X
# ESP32 Dev Module / MicroPython
#
# D22 SCL
# D21 SDA
# D18 XSHUT_1
# D19 XSHUT_2
# GND
# 3V3
#
# Baudrate: 115200

from machine import Pin, I2C
from time import sleep_ms
from vl53l0x import VL53L0X


# Neue I2C-Adressen
LOX1_ADDRESS = 0x30
LOX2_ADDRESS = 0x31

# XSHUT-Pins
SHT_LOX1 = 18
SHT_LOX2 = 19

# I2C Pins ESP32
I2C_SCL = 22
I2C_SDA = 21

# Standardadresse VL53L0X
VL53L0X_DEFAULT_ADDRESS = 0x29


# I2C initialisieren
i2c = I2C(
    0,
    scl=Pin(I2C_SCL),
    sda=Pin(I2C_SDA),
    freq=400000
)

# XSHUT Pins
xshut1 = Pin(SHT_LOX1, Pin.OUT)
xshut2 = Pin(SHT_LOX2, Pin.OUT)

lox1 = None
lox2 = None


def set_id():
    global lox1, lox2

    # Beide Sensoren ausschalten
    xshut1.value(0)
    xshut2.value(0)
    sleep_ms(10)

    # Beide kurz einschalten
    xshut1.value(1)
    xshut2.value(1)
    sleep_ms(10)

    # Sensor 1 aktivieren, Sensor 2 ausgeschaltet lassen
    xshut1.value(1)
    xshut2.value(0)
    sleep_ms(10)

    # Sensor 1 liegt jetzt auf Standardadresse 0x29
    lox1 = VL53L0X(i2c)
    lox1.set_address(LOX1_ADDRESS)
    sleep_ms(10)

    # Sensor 2 einschalten
    xshut2.value(1)
    sleep_ms(10)

    # Sensor 2 liegt jetzt noch auf Standardadresse 0x29
    lox2 = VL53L0X(i2c)
    lox2.set_address(LOX2_ADDRESS)
    sleep_ms(10)

    print("Sensoren initialisiert:")
    print("Sensor 1 Adresse:", hex(LOX1_ADDRESS))
    print("Sensor 2 Adresse:", hex(LOX2_ADDRESS))


def read_dual_sensors():
    try:
        distance1 = lox1.read()
    except Exception:
        distance1 = None

    try:
        distance2 = lox2.read()
    except Exception:
        distance2 = None

    print("1:", end=" ")
    if distance1 is not None and distance1 > 0:
        print("#1", distance1, "mm", end=" ")
    else:
        print("#1 Out of range", end=" ")

    print("2:", end=" ")
    if distance2 is not None and distance2 > 0:
        print("#2", distance2, "mm")
    else:
        print("#2 Out of range")


def main():
    print("Shutdown pins inited...")

    xshut1.value(0)
    xshut2.value(0)

    print("Both in reset mode...(pins are low)")
    print("Starting...")

    set_id()

    while True:
        read_dual_sensors()
        sleep_ms(100)


main()