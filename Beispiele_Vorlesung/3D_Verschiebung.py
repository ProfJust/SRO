import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.widgets import Slider

def get_cube_vertices():
    r = [-1, 1]
    return np.array([[x, y, z] for x in r for y in r for z in r])

faces = [
    [0, 1, 3, 2],
    [4, 5, 7, 6],
    [0, 1, 5, 4],
    [2, 3, 7, 6],
    [0, 2, 6, 4],
    [1, 3, 7, 5],
]

def translation_matrix(tx, ty, tz):
    return np.array([tx, ty, tz])

fig = plt.figure(figsize=(8, 7))
ax = fig.add_subplot(111, projection='3d')

slider_ax = plt.axes([0.25, 0.02, 0.5, 0.03])
slider = Slider(slider_ax, 'Verschiebung X', valmin=-3, valmax=3, valinit=0)

# Textfeld für Translationsvektor
trans_text = plt.figtext(0.13, 0.18, '', fontsize=13, family='monospace')

def plot_cube(ax, tx):
    ax.cla()
    T = translation_matrix(tx, 0, 0)
    verts = get_cube_vertices() + T
    cube = [[verts[j] for j in f] for f in faces]
    ax.add_collection3d(Poly3DCollection(cube, facecolors='magenta', linewidths=1, edgecolors='r', alpha=.25))
    ax.set_xlim(-4, 4)
    ax.set_ylim(-2, 2)
    ax.set_zlim(-2, 2)
    ax.set_box_aspect([2,1,1])
    ax.set_title(f"Würfelverschiebung: x = {tx:.2f}")

    text = f"Translationsvektor T =\n[{tx:6.2f}\n  0.00\n  0.00]"
    trans_text.set_text(text)

def update(val):
    plot_cube(ax, slider.val)
    plt.draw()

slider.on_changed(update)
plot_cube(ax, 0)
plt.show()
