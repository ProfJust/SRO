import numpy as np
import matplotlib.pyplot as plt

# Homogene  3x3-Matriz (für 2D) erstellen
# Drehung gegen Uhrzeigersinn um Z-Achse: angle
# Verschiebung in X-Richtung:  tx
# Verschiebung in Y-Richtung:  ty

def create_homogeneous_2d(angle, tx, ty):
    theta = np.radians(angle)
    cosT, sinT = np.cos(theta), np.sin(theta)
    return np.array([
        [cosT, -sinT, tx],
        [sinT,  cosT, ty],
        [0,  0, 1]
    ])

# Funktion für Transformation eines Punktes
def transform_point(matrix, point):
    point_hom = np.append(point, 1)  # Ergänze homogene Koordinate, z.B. [2. 0.] => [2. 0. 1.]
    transformed = matrix @ point_hom # @ => Matrix-Vektor-Multiplikation 
    print("Point", point, "Transformed => ", transformed, "bzw.", transformed[:2])
  
    # Rückkonvertierung zu kartesischen Koordinaten
    return transformed[:2]  # gibt die ersten beiden Werte zurück

#------------------------------------------------------------------
# Beispielpunkte und Transformation
points = np.array([[0,0], [1,0], [1,1], [0,1]])

# erstelle homogene Transformationsmatrix ,
# ====>>>  für Verschiebung um 2 entlang der X-Achse
#                            (angle in deg, tx, ty)
transformM = create_homogeneous_2d(90, 2, 1) 
print("Transformationsmatrix: \n",transformM)

# Transformiere die Punkte
transformed = np.array([transform_point(transformM, p) for p in points])

# Plot
fig, axes = plt.subplots()
axes.plot(*points.T, 'bo-', label="Original")
axes.plot(*transformed.T, 'ro-', label="Transformiert")
axes.axis('equal'); axes.legend()
plt.show()
