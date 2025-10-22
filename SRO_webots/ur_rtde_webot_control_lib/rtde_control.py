
import socket
import json

class RTDEControlInterface:
    def __init__(self, ip, port=30010):
        self.ip = ip
        self.port = port
        self.sock = socket.create_connection((ip, port))
        print(f"📡 Verbindung zu RTDE-Control-Schnittstelle unter {ip}:{port} hergestellt")

    def _send_command(self, command, data=None):
        message = {"command": command}
        if data:
            message["data"] = data
        self.sock.sendall(json.dumps(message).encode("utf-8"))
        response = self.sock.recv(4096).decode("utf-8")
        return json.loads(response)

    def moveJ(self, joint_angles):
        return self._send_command("moveJ", joint_angles)

    def moveL(self, cartesian_pose, speed=0.5, acceleration=0.3):
        return self._send_command("moveL", {"pose": cartesian_pose, "speed": speed, "acceleration": acceleration})

    def reset_to_home(self):
        return self._send_command("reset_to_home")

    def disconnect(self):
        return self._send_command("disconnect")
