"""
UR3e Gamepad Controller for Webots (Python)
------------------------------------------
Controls a UR3e robot in Webots using a standard gamepad via pygame.

Changes vs v1
- Auto-detects gripper joint limits and drives full travel (open/close)
- Latching gripper target (keeps last command)
- Sets velocity and available torque/force (if supported) for strong closing
- Same 5-axes + buttons scheme for 6 joints

Usage
1) pip install pygame
2) Assign as controller of your UR3e Robot node in Webots
3) Hold Deadman button to move (see mapping below)
"""

from controller import Robot, Motor
import math
import time

try:
    import pygame
    _HAVE_PYGAME = True
except Exception:
    _HAVE_PYGAME = False

# ----------------------------- Configuration ---------------------------------
DEADMAN_BUTTON = 4  # LB (Xbox/Logitech typical)

WRIST3_POS_BTN = 5   # RB: + direction
WRIST3_NEG_BTN = 6   # Back/View: - direction (adjust as needed)

SPEED_SLOW_BTN   = 0  # A
SPEED_NORMAL_BTN = 1  # B
SPEED_FAST_BTN   = 3  # Y

GRIPPER_CLOSE_BTN = 2  # X
GRIPPER_OPEN_BTN  = 7  # Start/Menu

# Axis → joint mapping (5 analog axes) for first 5 joints
AXIS_TO_JOINT = {
    0: 0,  # LX  → shoulder_pan
    1: 1,  # LY  → shoulder_lift (inverted below)
    3: 2,  # RY  → elbow (inverted below)
    2: 3,  # RX  → wrist_1
    4: 4,  # RT/LT axis → wrist_2
}

JOINT_MAX_VEL = [1.5, 1.5, 1.8, 2.2, 2.2, 2.5]
WRIST3_BUTTON_VEL = 1.8

SPEED_SCALES = {
    'slow':   0.25,
    'normal': 0.6,
    'fast':   1.0,
}
DEFAULT_SCALE = 'normal'

DEADZONE = 0.12
SMOOTHING = 0.25

POSSIBLE_JOINT_NAMES = [
    ["shoulder_pan_joint", "shoulder_pan"],
    ["shoulder_lift_joint", "shoulder_lift"],
    ["elbow_joint", "elbow"],
    ["wrist_1_joint", "wrist_1"],
    ["wrist_2_joint", "wrist_2"],
    ["wrist_3_joint", "wrist_3"],
]

GRIPPER_JOINT_CANDIDATES = [
    # "robotiq_85_left_finger_joint",  
    # "robotiq_85_right_finger_joint",
    # "left_finger_joint",
    # "right_finger_joint",
    # "gripper_finger_joint",
    "ROBOTIQ 2F-85 Gripper::left finger joint",  
    "ROBOTIQ 2F-85 Gripper::right finger joint",
]

# Auto-range gripper parameters
GRIPPER_SPEED   = 0.8
GRIPPER_TORQUE  = 8.0   # Nm for rotational fingers (if supported)
GRIPPER_FORCE   = 120.0 # N  for linear fingers (if supported)
DEFAULT_GRIPPER_TARGET = 0.0  # 0=open, 1=close (latched)

# ------------------------------ Helpers --------------------------------------

def apply_deadzone(x, dz=DEADZONE):
    return 0.0 if abs(x) < dz else x


def smooth(prev, new, alpha=SMOOTHING):
    return prev * alpha + new * (1 - alpha)


def get_motor(robot: Robot, names):
    for n in names:
        m = robot.getDevice(n) if n else None
        if isinstance(m, Motor):
            return m
    return None

# ------------------------------ Controller -----------------------------------
class UR3eGamepadController:
    def __init__(self):
        self.robot = Robot()
        self.timestep = int(self.robot.getBasicTimeStep())

        # Acquire arm joints
        self.joints = []
        for name_list in POSSIBLE_JOINT_NAMES:
            m = get_motor(self.robot, name_list)
            if m is None:
                raise RuntimeError(f"Joint not found for any of names: {name_list}")
            self.joints.append(m)
        for j in self.joints:
            j.setPosition(float('inf'))
            j.setVelocity(0.0)

        # Detect gripper fingers and their limits
        self.gripper = []  # list of dicts: {motor,min,max}
        for candidate in GRIPPER_JOINT_CANDIDATES:
            m = self.robot.getDevice(candidate)
            if isinstance(m, Motor):
                try:
                    mn = m.getMinPosition()
                except Exception:
                    mn = None
                try:
                    mx = m.getMaxPosition()
                except Exception:
                    mx = None
                if mn is None or mx is None:
                    mn, mx = -0.04, 0.04  # conservative defaults
                if mx < mn:
                    mn, mx = mx, mn
                try:
                    m.setVelocity(GRIPPER_SPEED)
                except Exception:
                    pass
                try:
                    m.setAvailableTorque(GRIPPER_TORQUE)
                except Exception:
                    pass
                try:
                    m.setAvailableForce(GRIPPER_FORCE)
                except Exception:
                    pass
                self.gripper.append({"motor": m, "min": mn, "max": mx})
        if self.gripper:
            print("[INFO] Gripper joints detected:")
            for g in self.gripper:
                print(f"  - {g['motor'].getName()} limits: [{g['min']:.4f}, {g['max']:.4f}]")

        # Gamepad state
        self.scale_key = DEFAULT_SCALE
        self.scale = SPEED_SCALES[self.scale_key]
        self.filtered_cmd = [0.0] * 6
        self.gripper_target = DEFAULT_GRIPPER_TARGET

        # Init pygame
        self.joy = None
        if _HAVE_PYGAME:
            pygame.init()
            pygame.joystick.init()
            if pygame.joystick.get_count() == 0:
                print("[WARN] No gamepad found. Controller will idle.")
            else:
                self.joy = pygame.joystick.Joystick(0)
                self.joy.init()
                print(f"[INFO] Using gamepad: {self.joy.get_name()}")
                print(f"       Axes={self.joy.get_numaxes()} Buttons={self.joy.get_numbuttons()} Hats={self.joy.get_numhats()}")
        else:
            print("[WARN] pygame not available. Install pygame to enable gamepad control.")

        self._last_print = time.time()

    def _update_speed_scale(self, btn):
        if btn.get(SPEED_SLOW_BTN):
            self.scale_key = 'slow'
        elif btn.get(SPEED_NORMAL_BTN):
            self.scale_key = 'normal'
        elif btn.get(SPEED_FAST_BTN):
            self.scale_key = 'fast'
        self.scale = SPEED_SCALES[self.scale_key]

    def _handle_gripper(self, btn):
        if not self.gripper:
            return
        # Latch updates
        if btn.get(GRIPPER_CLOSE_BTN):
            self.gripper_target = 1.0
        elif btn.get(GRIPPER_OPEN_BTN):
            self.gripper_target = 0.0
        # Apply to all finger joints every step
        for g in self.gripper:
            m = g["motor"]
            mn, mx = g["min"], g["max"]
            # 0=open at mx, 1=close at mn (full stroke)
            target = mn + (1.0 - self.gripper_target) * (mx - mn)
            try:
                m.setPosition(target)
            except Exception:
                pass

    def _read_gamepad(self):
        axes = {}
        buttons = {}
        deadman = False
        if self.joy is None:
            return axes, buttons, deadman
        pygame.event.pump()
        for a in AXIS_TO_JOINT.keys():
            if a < self.joy.get_numaxes():
                v = self.joy.get_axis(a)
                axes[a] = apply_deadzone(v)
            else:
                axes[a] = 0.0
        for b in range(self.joy.get_numbuttons()):
            buttons[b] = bool(self.joy.get_button(b))
        deadman = buttons.get(DEADMAN_BUTTON, False)
        return axes, buttons, deadman

    def _axes_to_joint_vel(self, axes, buttons, deadman):
        cmd = [0.0] * 6
        if not deadman:
            return cmd
        for axis_idx, joint_idx in AXIS_TO_JOINT.items():
            val = axes.get(axis_idx, 0.0)
            if axis_idx in (1, 3):  # invert vertical sticks
                val = -val
            cmd[joint_idx] = val * JOINT_MAX_VEL[joint_idx] * self.scale
        w3 = 0.0
        if buttons.get(WRIST3_POS_BTN, False):
            w3 += WRIST3_BUTTON_VEL * self.scale
        if buttons.get(WRIST3_NEG_BTN, False):
            w3 -= WRIST3_BUTTON_VEL * self.scale
        cmd[5] = w3
        return cmd

    def step(self):
        axes, buttons, deadman = self._read_gamepad()
        self._update_speed_scale(buttons)
        self._handle_gripper(buttons)
        target = self._axes_to_joint_vel(axes, buttons, deadman)

        for i in range(6):
            self.filtered_cmd[i] = smooth(self.filtered_cmd[i], target[i])
            try:
                self.joints[i].setVelocity(self.filtered_cmd[i])
            except Exception:
                pass

        now = time.time()
        if now - self._last_print > 1.0:
            self._last_print = now
            print(f"mode={self.scale_key} deadman={'ON' if deadman else 'off'} v={[round(v,3) for v in self.filtered_cmd]} gripper={self.gripper_target}")

        return self.robot.step(self.timestep)

if __name__ == "__main__":
    ctrl = UR3eGamepadController()
    while ctrl.step() != -1:
        pass
