import pygame  # ggf. pip install pygame
import sys

# PyGame initialisieren
pygame.init()
pygame.joystick.init()

# Prüfen, ob ein Joystick gefunden wurde
if pygame.joystick.get_count() == 0:
    print("❌ Kein Gamepad gefunden! - Programm wird beendet.")
    print("   Bitte schließe ein Gamepad an teste den Windows-Treiber ")
    print("   Win + R → joy.cpl → Eigenschaften → Testen")

    sys.exit()
else:
    print(f"✅ {pygame.joystick.get_count()} Gamepad(s) gefunden.")

# Erstes Gamepad auswählen
joystick = pygame.joystick.Joystick(0)
joystick.init()
print(f"🎮 Verwende: {joystick.get_name()}")
print(f"   Achsen: {joystick.get_numaxes()}")
print(f"   Knöpfe: {joystick.get_numbuttons()}")
print(f"   Hats:   {joystick.get_numhats()}")

print("\nDrücke STRG+C zum Beenden.\n")

# Hauptloop
try:
    while True:
        # Events abrufen
        for event in pygame.event.get():
            if event.type == pygame.JOYAXISMOTION:
                axes = [round(joystick.get_axis(i), 3) for i in range(joystick.get_numaxes())]
                print(f"Achsen: {axes}")
            elif event.type == pygame.JOYBUTTONDOWN:
                print(f"🔘 Button {event.button} gedrückt")
            elif event.type == pygame.JOYBUTTONUP:
                print(f"⚪ Button {event.button} losgelassen")
            elif event.type == pygame.JOYHATMOTION:
                print(f"🎯 Hat bewegt: {event.value}")

        # kurze Pause, damit CPU geschont wird
        pygame.time.wait(50)

except KeyboardInterrupt:
    print("\nBeende Programm…")
finally:
    pygame.quit()
