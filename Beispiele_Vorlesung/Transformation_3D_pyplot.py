import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D


# Homogene  4x4-Matrix (für 3D) erstellen
# Drehung gegen Uhrzeigersinn um Z-Achse: angle
# Verschiebung in X-Richtung:  tx
# Verschiebung in Y-Richtung:  ty

def create_homogeneous_3d(angle_x, angle_y, angle_z, tx, ty, tz):
    rx, ry, rz = np.radians([angle_x, angle_y, angle_z])
    Rx = np.array([
        [1, 0, 0, 0],
        [0, np.cos(rx), -np.sin(rx), 0],
        [0, np.sin(rx), np.cos(rx), 0],
        [0, 0, 0, 1]
    ])
    Ry = np.array([
        [np.cos(ry), 0, np.sin(ry), 0],
        [0, 1, 0, 0],
        [-np.sin(ry), 0, np.cos(ry), 0],
        [0, 0, 0, 1]
    ])
    Rz = np.array([
        [np.cos(rz), -np.sin(rz), 0, 0],
        [np.sin(rz), np.cos(rz), 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ])
    R = Rz @ Ry @ Rx
    T = np.eye(4)
    T[:3, 3] = [tx, ty, tz]
    return T @ R
# Funktion für Transformation eines Punktes
def transform_point_3d(matrix, point):
    point_hom = np.append(point, 1)
    transformed = matrix @ point_hom
    return transformed[:3]
#------------------------------------------------------------------
# Beispielpunkte und Transformation
# points = np.array([[0,0], [1,0], [1,1], [0,1]])
points_3d = np.array([[0, 0, 0], [1, 0, 0]]) # , [1, 1, 0], [0, 1, 0]

# erstelle homogene Transformationsmatrix, für Verschiebung um 2 entlang der X-Achse und 1 na Y-Achse
transformM = create_homogeneous_3d(0, 0, 0.6, 2, 1, 0)   #(angle_x, angle_y, angle_z, tx, ty, tz)
print("Transformationsmatrix: \n",transformM)

# Transformiere die Punkte
transformed_points = np.array([transform_point_3d(transformM, p) for p in points_3d])

# Plot
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
ax.scatter(points_3d[:, 0], points_3d[:, 1], points_3d[:, 2], c='b', label='Original')
ax.scatter(transformed_points[:, 0], transformed_points[:, 1], transformed_points[:, 2], c='r', label='Transformiert')

# Verbindungslinien
for i in range(len(points_3d)):
    ax.plot([points_3d[i, 0], transformed_points[i, 0]],
            [points_3d[i, 1], transformed_points[i, 1]],
            [points_3d[i, 2], transformed_points[i, 2]], 'k--')

ax.legend()
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
plt.show()
