import rtde_receive
import rtde_control
import time

UR3_IP = "127.0.0.1"  # Simulationsserver/Webots-Instanz

# RTDE-Verbindungen aufbauen
rtde_r = rtde_receive.RTDEReceiveInterface(UR3_IP)
rtde_c = rtde_control.RTDEControlInterface(UR3_IP)

# Aktuelle Gelenkwinkel abrufen
actual_q = rtde_r.getActualQ()
print(f"📍 Aktuelle Gelenkposition: {actual_q}\n")

# Liste von kartesischen Zielposen (Dummy → direkt als joint angles interpretiert)
moveL_ziele = [
    [-0.5, -1.0, 0.50, 0.0, 3.1, 0.0],   # weiter hinten, höher
    [-0.2, -0.8, 0.55, 0.0, 3.1, 0.2],   # leicht gedreht
    [ 0.0, -0.6, 0.45, 0.0, 3.1, -0.1],  # zentral
    [ 0.3, -1.1, 0.50, 0.0, 3.0, 0.3],   # deutlich rechts
    [-0.3, -0.7, 0.40, 0.0, 3.2, 0.1],   # links vorne unten
]

# Bewegungen ausführen
for i, ziel_pose in enumerate(moveL_ziele):
    print(f"➡️  Sende moveL #{i+1}: {ziel_pose}")
    resp = rtde_c.moveL(ziel_pose, speed=0.5, acceleration=0.3)
    print(f"📥 Antwort: {resp}")
    time.sleep(3)

# Endgültige Gelenkposition auslesen
final_q = rtde_r.getActualQ()
print(f"\n📍 Gelenkposition nach allen Bewegungen: {final_q}")

# Verbindung trennen
rtde_c.disconnect()
rtde_r.disconnect()
