# Hama Gamepad steuert UR3e - Roboter 4
# Ziel => real UR3e per Gamepad bewegen 
# Deadman Taste (L1) gedrückt halten zum Verfahren,
# Linker Stick: X/Y Translation,
# R1/R2: Z hoch/runter

# Last edited by Olaf Just at 11.05.2026
# tested with UR3e - Roboter 4

import time
import pygame
import rtde_control

ROBOT_IP = "192.168.0.17"  # UR3e - Roboter 4 

# Sicherheitsbegrenzungen
MAX_TRANS_SPEED = 0.03      # m/s
MAX_ROT_SPEED = 0.02        # rad/s
ACC = 0.02                  # Jog-Beschleunigung
DEADZONE = 0.12

# Feature: Basis-Koordinatensystem
FEATURE_BASE = rtde_control.RTDEControlInterface.FEATURE_BASE

# Gamepad-Zuordnung
AXIS_LX = 0      # links/rechts -> Y
AXIS_LY = 1      # vor/zurück -> X
AXIS_RX = 3      # rechter Stick X -> Rz
AXIS_RY = 4      # rechter Stick Y -> Z
BUTTON_R1 = 5    # rechte obere Schultertaste
BUTTON_R2 = 7    # rechte untere Schultertaste,
DEADMAN_BUTTON = 4   # L1 gedrückt halten


def apply_deadzone(value, deadzone=DEADZONE):
    if abs(value) < deadzone:
        return 0.0
    return value


def main():
    print("\a THIS SOFTWARE IS UNDER HEAVY CONSTRUCTION ")
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        raise RuntimeError("Kein Gamepad gefunden.")

    joystick = pygame.joystick.Joystick(0)
    joystick.init()

    print(f"Gamepad erkannt: {joystick.get_name()}")
    print("Deadman-Taste (Links L 1) gedrückt halten zum Verfahren.")
    print("Strg+C beendet das Programm.")

    rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)

    jogging_active = False

    try:
        while True:
            pygame.event.pump()

            deadman = joystick.get_button(DEADMAN_BUTTON)
            up      = joystick.get_button(BUTTON_R1)
            down    = joystick.get_button(BUTTON_R2)

            if deadman:
                lx = apply_deadzone(joystick.get_axis(AXIS_LX))
                ly = apply_deadzone(joystick.get_axis(AXIS_LY))
                rx = apply_deadzone(joystick.get_axis(AXIS_RX))
                # ry = apply_deadzone(joystick.get_axis(AXIS_RY))
                if up:
                    lz = 1.0
                elif down:
                    lz = -1.0
                else:
                    lz = 0.0

                # jogStart erwartet: [vx, vy, vz, rx, ry, rz]
                # Translation: mm/s, Rotation: rad/s
                speed_vector = [
                    ly * MAX_TRANS_SPEED,   # X vor/zurück
                    lx * MAX_TRANS_SPEED,    # Y links/rechts
                    lz * MAX_TRANS_SPEED,   # Z hoch/runter
                    0.0,                     # Rotation um X
                    0.0,                     # Rotation um Y
                    rx * MAX_ROT_SPEED       # Rotation um Z
                ]

                rtde_c.jogStart(speed_vector, FEATURE_BASE, ACC)
                jogging_active = True           
            else:
                if jogging_active:
                    rtde_c.jogStop()
                    jogging_active = False

            time.sleep(0.02)  # ca. 50 Hz

    except KeyboardInterrupt:
        print("Programm wird beendet.")
    
    except RuntimeError as e:
        print("RTDE-/Roboterfehler:")
        print(e)

    except Exception as e:
        print("Allgemeiner Fehler:")
        print(e)

    finally:
        print("Stoppe Roboter und beende RTDE-Verbindung...")
        try:
            rtde_c.jogStop()
        except Exception:
            pass
        
        try:
            rtde_c.stopScript()
        except Exception:
            pass

        try:
            rtde_c.disconnect()
        except Exception:
            print("disconnect nicht möglich:", e)

        pygame.quit()


if __name__ == "__main__":
    main()