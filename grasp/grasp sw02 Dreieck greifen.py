import cv2
import numpy as np
import math

def find_triangle_grasp_angle(contour):
    # Kontur zu Polygon vereinfachen
    epsilon = 0.03 * cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, epsilon, True)

    if len(approx) != 3:
        return None, None

    pts = approx.reshape(3, 2)

    # Kanten berechnen
    edges = []
    for i in range(3):
        p1 = pts[i]
        p2 = pts[(i + 1) % 3]

        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]

        length = math.sqrt(dx*dx + dy*dy)
        angle = math.atan2(dy, dx)

        edges.append((length, angle, p1, p2))

    # längste Kante suchen
    longest_edge = max(edges, key=lambda e: e[0])
    length, angle_rad, p1, p2 = longest_edge

    angle_deg = math.degrees(angle_rad)

    return angle_deg, pts