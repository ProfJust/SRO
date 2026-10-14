""" Erstellt mehrere ARUCO Marker"""
import cv2
from cv2 import aruco
import matplotlib.pyplot as plt

aruco_dict = aruco.getPredefinedDictionary(
    aruco.DICT_5X5_250
)

fig = plt.figure(figsize=(8, 8))

for i in range(1, 5):
    ax = fig.add_subplot(2, 2, i)

    img = aruco.generateImageMarker(
        aruco_dict,
        i,
        500
    )

    ax.imshow(img, cmap="gray")
    ax.set_title(f"ID {i}")
    ax.axis("off")

plt.show()