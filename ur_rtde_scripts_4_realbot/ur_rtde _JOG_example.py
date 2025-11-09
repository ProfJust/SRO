# jog-example https://sdurobotics.gitlab.io/ur_rtde/examples/examples.html
# changed to Python
# Ziel => real UR3e per Gamepad steuern

### MAKE A BEEP ###
print(" THIS SOFTWARE IS UNDER HEAVY CONSTRUCTION ")
import pygame
pygame.mixer.init()
sound = pygame.mixer.Sound('owin31.wav')
sound.play()

import rtde_control
import msvcrt
import time

ROBOT_IP = "192.168.0.3"
rtde_c = rtde_control.RTDEControlInterface("ROBOT_IP")
speed_magnitude = 0.15
speed_vector = [0, 0, 0, 0, 0, 0]

try:
    while True:
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'H':  # Up arrow
                speed_vector = [0, 0, -speed_magnitude, 0, 0, 0]
            elif key == b'P':  # Down arrow
                speed_vector = [0, 0, speed_magnitude, 0, 0, 0]
            elif key == b'K':  # Left arrow
                speed_vector = [speed_magnitude, 0, 0, 0, 0, 0]
            elif key == b'M':  # Right arrow
                speed_vector = [-speed_magnitude, 0, 0, 0, 0, 0]
            elif key == b'q':
                break
            else:
                speed_vector = [0, 0, 0, 0, 0, 0]
            rtde_c.jogStart(speed_vector, rtde_control.RTDEControlInterface.FEATURE_TOOL)
        time.sleep(0.02)
finally:
    rtde_c.jogStop()
    rtde_c.stopScript()
