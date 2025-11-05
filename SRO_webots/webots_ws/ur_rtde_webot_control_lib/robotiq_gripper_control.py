class RobotiqGripper:
    def __init__(self, rtde_control):
        self.rtde = rtde_control
        self._position = 0  # Simulierte Position (0=geschlossen, 255=offen)

    def connect(self, ip, port=30010):
        # Dient nur der Kompatibilität mit echtem RTDE-Gripper-Modul
        print(f"Gripper verbunden")

    def activate(self):
        return self.rtde._send_command("activate")

    def open(self):
        self._position = 255
        return self.rtde._send_command("openGripper")

    def close(self):
        self._position = 0
        return self.rtde._send_command("closeGripper")

    def move(self, value):  # mm
        return self.rtde._send_command("move", {"value": value})

    def set_force(self, value):
        return self.rtde._send_command("set_force", {"value": value})

    def set_speed(self, value):
        return self.rtde._send_command("set_speed", {"value": value})

    def move_and_wait_for_pos(self, position, speed, force):
        # 0 = geschlossen, 255 = offen
        self._position = position
        if position <= 10:
            return self.close()
        else:
            return self.open()

    def get_current_position(self):
        return self._position

    def is_open(self):
        return self._position > 200

    def is_closed(self):
        return self._position < 20
