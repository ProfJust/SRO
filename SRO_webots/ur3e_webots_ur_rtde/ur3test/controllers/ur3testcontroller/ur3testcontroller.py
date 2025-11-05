from controller import Robot
import socket
import threading
import json

# RTDE-Schnittstellenparameter
SERVER_HOST = "0.0.0.0"  # Nicht die Adresse des  Clients 127.0.0.1
SERVER_PORT = 30010

# Initialisiere den Webots-Roboter
robot = Robot()
timestep = int(robot.getBasicTimeStep())

# UR3e Gelenknamen (wie im UR3e PROTO definiert)
joint_names = [
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "elbow_joint",
    "wrist_1_joint",
    "wrist_2_joint",
    "wrist_3_joint"
]

# Initialisiere Motoren und Sensoren
motors = {}
sensors = {}
for name in joint_names:
    motor = robot.getDevice(name)
    sensor = robot.getDevice(name + "_sensor")
    if motor:
        motors[name] = motor
    if sensor:
        sensor.enable(timestep)
        sensors[name] = sensor

# Globale Variablen
current_joint_angles = [0.0] * len(joint_names)
target_joint_angles = None
lock = threading.Lock()

# Dummy-Inverse-Kinematik (hier: kartesische Pose direkt als Gelenkwinkel)
def inverse_kinematics(cartesian_pose):
    if len(cartesian_pose) != 6:
        return None
    return cartesian_pose  # dummy: einfach zurückgeben

# Netzwerkkommunikation
def handle_client(conn, addr):
    print(f"🔗 Neue RTDE-Verbindung von {addr}")
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            try:
                request = json.loads(data.decode("utf-8"))
            except json.JSONDecodeError:
                response = {"error": "Ungültiges JSON"}
                conn.sendall(json.dumps(response).encode("utf-8"))
                continue

            command = request.get("command")
            response = {}

            if command == "getActualQ":
                with lock:
                    response = {"data": current_joint_angles.copy()}

            elif command == "moveJ":
                joint_targets = request.get("data")
                if isinstance(joint_targets, list) and len(joint_targets) == 6:
                    with lock:
                        global target_joint_angles
                        target_joint_angles = joint_targets.copy()
                    response = {"info": "moveJ akzeptiert", "target_q": joint_targets}
                else:
                    response = {"error": "Ungültige Gelenkwinkel für moveJ"}

            elif command == "moveL":
                data = request.get("data", {})
                pose = data.get("pose")
                speed = data.get("speed", 0.5)
                acceleration = data.get("acceleration", 0.3)
                if isinstance(pose, list) and len(pose) == 6:
                    ik_solution = inverse_kinematics(pose)
                    if ik_solution:
                        with lock:
                            target_joint_angles = ik_solution.copy()
                        response = {
                            "info": "moveL akzeptiert (dummy IK)",
                            "target_q": ik_solution,
                            "speed": speed,
                            "acceleration": acceleration
                        }
                    else:
                        response = {"error": "IK konnte keine Lösung finden"}
                else:
                    response = {"error": "Ungültige Pose für moveL"}

            elif command == "disconnect":
                response = {"info": "Verbindung getrennt"}
                conn.sendall(json.dumps(response).encode("utf-8"))
                break

            else:
                response = {"error": f"Unbekannter Befehl: {command}"}

            conn.sendall(json.dumps(response).encode("utf-8"))

    except Exception as e:
        print(f"❌ Fehler mit {addr}: {e}")
    finally:
        conn.close()
        print(f"❌ Verbindung zu {addr} geschlossen")

def server_thread():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind((SERVER_HOST, SERVER_PORT))
    server_sock.listen()
    print(f"🚀 RTDE-Server aktiv auf {SERVER_HOST}:{SERVER_PORT}")
    while True:
        conn, addr = server_sock.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

# Starte TCP-Server-Thread
threading.Thread(target=server_thread, daemon=True).start()

# Webots-Hauptschleife
while robot.step(timestep) != -1:
    # Gelenkwinkel auslesen
    with lock:
        current_joint_angles = [
            sensors[name].getValue() if name in sensors else 0.0
            for name in joint_names
        ]

        # Zielgelenkwinkel setzen
        if target_joint_angles:
            for name, angle in zip(joint_names, target_joint_angles):
                if name in motors:
                    motors[name].setPosition(angle)
            target_joint_angles = None
