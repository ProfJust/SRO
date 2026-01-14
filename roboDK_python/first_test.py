from robodk.robolink import *   # RoboDK API ggf. pip install robodk
from robodk.robomath import *

RDK = Robolink()

robot = RDK.Item('UR3e', ITEM_TYPE_ROBOT)
if not robot.Valid():
    raise RuntimeError("Robot 'UR3e' nicht gefunden (Name im Station Tree prüfen).")

# Optional: Kollisionsprüfung einschalten
# RDK.setCollisionActive(1)

prog = RDK.AddProgram("UR3e_AutoProg", robot)

def tgt(name: str):
    t = RDK.Item(name, ITEM_TYPE_TARGET)
    if not t.Valid():
        raise RuntimeError(f"Target '{name}' nicht gefunden.")
    return t

# Beispiel-Sequenz: MoveJ + kurze MoveL Approaches
prog.MoveJ(tgt("Target 1"))

for p in ["Target 2", "Target 3"]:
    prog.MoveJ(tgt(p))
    prog.Pause(2000)
    # prog.MoveJ(tgt(f"{p}_Approach"))
    # prog.MoveL(tgt(p))
    # Greiferbefehle optional:
    # prog.RunInstruction("GripperClose()", INSTRUCTION_CALL_PROGRAM)
    # prog.MoveL(tgt(f"{p}_Retract"))
prog.Pause(2000)
prog.MoveJ(tgt("Target 1"))

print("Programm in RoboDK erstellt. Export über 'Generate robot program' in RoboDK.")
