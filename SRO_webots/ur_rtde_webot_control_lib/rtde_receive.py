# sim_rtde_receive.py

import socket
import json

class RTDEReceiveInterface:
    def __init__(self, ip, port=30010):
        self.ip = ip
        self.port = port
        self.sock = socket.create_connection((ip, port))
        print(f"📡 Verbindung zu Sim-RTDE-Server unter {ip}:{port} hergestellt")

    def getActualQ(self):
        self._send_command("getActualQ")
        return self._receive_response()

    def disconnect(self):
        self._send_command("disconnect")
        self.sock.close()
        print("🔌 Verbindung zum Sim-RTDE-Server getrennt")

    def _send_command(self, command):
        message = json.dumps({"command": command})
        self.sock.sendall(message.encode("utf-8"))

    def _receive_response(self):
        data = self.sock.recv(4096).decode("utf-8")
        return json.loads(data).get("data", [])