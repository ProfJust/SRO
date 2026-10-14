""" Erstellt einen ARUCO Marker"""
#!/usr/bin/env python3

import cv2
from cv2 import aruco
import matplotlib.pyplot as plt
import matplotlib as mpl

# Dictionary auswählen
aruco_dict = aruco.getPredefinedDictionary(
    aruco.DICT_5X5_250
)

# Marker erzeugen
marker_id = 1
marker_size = 700

img = aruco.generateImageMarker(
    aruco_dict,
    marker_id,
    marker_size
)

plt.imshow(img, cmap=mpl.cm.gray)
plt.axis("off")

plt.savefig("aruco_1.png")
plt.show()