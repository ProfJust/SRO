from pathlib import Path
from ikpy.chain import Chain
from math import pi
# Um das URDF im selben Dateipfad zu finden ...
script_dir = Path(__file__).parent
urdf_path = script_dir / "UR3e_ikpy_tcp.urdf"  # URDF exported from Webots

# Kinematische Kette bilden
robot = Chain.from_urdf_file(str(urdf_path))

# Vorwärts
for i, link in enumerate(robot.links):
    print(i, link.name)
angles_deg = [0.0, -90.0, 0.0, -180.0, 0.0, 0.0]
angles_rad = [float(pi / 180.0) * val for val in angles_deg]

print("Winkel des UR3e \n", angles_deg, "\n", angles_rad)

# IKPy erwartet 8 Werte: [Basis-Dummy, 6 Gelenke]
angles_rad_ikpy = [0.0] + [0.0] + angles_rad + [0.0]


fk = robot.forward_kinematics(angles_rad_ikpy)
print("FK", fk[0][3], fk[1][3], fk[2][3])
print(f"X = {fk[0][3]*1000:.2f} mm")
print(f"Y = {fk[1][3]*1000:.2f} mm")
print(f"Z = {fk[2][3]*1000:.2f} mm")

# to be done: IK
target_position = [fk[0][3],fk[1][3], fk[2][3]]
angles = robot.inverse_kinematics(target_position)
print(angles)
angl_deg = [float(180.0 / pi) * val for val in angles]
print(angl_deg )