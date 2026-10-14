# mpremote connect COM3 run .\sw01_LED_blink.py
# Dieses Skript blinkt die eingebaute LED des ESP32 (meistens auf GPIO2)
from machine import Pin
import time

# Blink the on-board LED (GPIO2) and an external LED (GPIO8) every second
# LED ist bei ESP32 meistens auf GPIO2, 
# oder auf GPIO8. Das kann je nach Board variieren. 
led =  Pin(2, Pin.OUT)
#led2 = Pin(4, Pin.OUT)
i = 0
while True:
    print("laeuft", i)
    i+=1
    led.value(1)
    #led2.value(1)
    time.sleep(1.0)

    led.value(0)
    #led2.value(0)
    time.sleep(2.0)
