import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.widgets import Slider

# Würfel-Eckpunkte
def get_cube_vertices():
    r = [-1, 1]
    vertices = np.array([[x, y, z] for x in r for y in r for z in r])
    return vertices

# Würfel-Flächen (je 4 Indizes für die Eckpunkte der Fläche)
faces = [
    [0, 1, 3, 2],
    [4, 5, 7, 6],
    [0, 1, 5, 4],
    [2, 3, 7, 6],
    [0, 2, 6, 4],
    [1, 3, 7, 5],
]

# Rotationsmatrix um die y-Achse
def rot_y(angle):
    theta = np.deg2rad(angle)
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])

# Plot-Funktion
def plot_cube(ax, angle):
    ax.cla()
    verts = get_cube_vertices() @ rot_y(angle).T
    cube = [[verts[j] for j in f] for f in faces]
    ax.add_collection3d(Poly3DCollection(cube, facecolors='cyan', linewidths=1, edgecolors='r', alpha=.25))
    ax.set_xlim(-2, 2)
    ax.set_ylim(-2, 2)
    ax.set_zlim(-2, 2)
    ax.set_box_aspect([1,1,1])
    ax.set_title(f"Würfelrotation: {angle:.1f}°")

# Figur und Achsen erstellen
fig = plt.figure(figsize=(8, 6))
ax = fig.add_subplot(111, projection='3d')

# Slider für den Rotationswinkel
slider_ax = plt.axes([0.25, 0.02, 0.5, 0.03])
slider = Slider(slider_ax, 'Rotation Y', valmin=0, valmax=360, valinit=0)

# Update-Funktion für Slider
def update(val):
    plot_cube(ax, slider.val)
    plt.draw()

slider.on_changed(update)
plot_cube(ax, 0)
plt.show()
