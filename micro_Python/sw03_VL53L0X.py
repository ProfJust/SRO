
from machine import Pin
from machine import SoftI2C
from lib.vl53l0x import VL53L0X

i2c = SoftI2C(scl=Pin(21),sda=Pin(22))

# Create a VL53L0X object
tof = VL53L0X.VL53L0X(i2c)
tof.set_Vcsel_pulse_period(tof.vcsel_period_type[0], 18)
tof.set_Vcsel_pulse_period(tof.vcsel_period_type[1], 14)
tof.start()


print("started")
while True:
    print(tof.read())
