import socket
import json

class RTDEControlInterface:
    def __init__(self, ip, port=30010):
        self.ip = ip
        self.port = port
        self.sock = socket.create_connection((ip, port))
        print(f"📡 Verbindung zu RTDE-Control-Schnittstelle unter {ip}:{port} hergestellt")

    def moveJ(self, joint_angles):
        message = json.dumps({"command": "moveJ", "data": joint_angles})
        self.sock.sendall(message.encode("utf-8"))
        response = self.sock.recv(4096).decode("utf-8")
        return json.loads(response)

    def moveL(self, cartesian_pose, speed=0.5, acceleration=0.3):
        message = json.dumps({
            "command": "moveL",
            "data": {
                "pose": cartesian_pose,
                "speed": speed,
                "acceleration": acceleration
            }
        })
        self.sock.sendall(message.encode("utf-8"))
        response = self.sock.recv(4096).decode("utf-8")
        return json.loads(response)

    def disconnect(self):
        message = json.dumps({"command": "disconnect"})
        self.sock.sendall(message.encode("utf-8"))
        self.sock.close()
        print("🔌 Verbindung zur RTDE-Control-Schnittstelle getrennt")
