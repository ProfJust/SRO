from pathlib import Path
from ikpy.chain import Chain
from math import pi
# Um das URDF im selben Dateipfad zu finden ...
script_dir = Path(__file__).parent
urdf_path = script_dir / "UR3e.urdf"  # URDF exported from Webots

# Kinematische Kette bilden
robot = Chain.from_urdf_file(
    str(urdf_path),
    # active_links_mask=[False, True, True, True, True, True, True]
    # da die erste Zeile meist ein Dummy-Origin-Link ist
    # => active_links_mask=[False, True, True, True, True, True, True]
)   

# Start: Eine TCP-Position in [x,y,z]
target_position = [0.3, 0.2, 0.4]
print("target position", target_position)
angles = robot.inverse_kinematics(target_position)
print("IK - Ermittelete Gelenkwinkel für diese TargetPos \n", angles)

print("\n Rückwärts: Target Position aus den Angles\n")
fk = robot.forward_kinematics(angles) # => 4x3 Matrix
print("FK", fk[0][3], fk[1][3], fk[2][3]) # nur letzte Spalte

# Vorwärts
for i, link in enumerate(robot.links):
    print(i, link.name)
angles_deg = [0.0, -90.0, 0.0, -180.0, 0.0, 0.0]
angles_rad = [float(pi / 180.0) * val for val in angles_deg]

print("Winkel des UR3e \n", angles_deg, "\n", angles_rad)

# IKPy erwartet 8 Werte: [Basis-Dummy, 6 Gelenke]
angles_rad_ikpy = [0.0] + [0.0] + angles_rad

fk = robot.forward_kinematics(angles_rad_ikpy)
print("FK", fk[0][3], fk[1][3], fk[2][3])
# print(fk)
