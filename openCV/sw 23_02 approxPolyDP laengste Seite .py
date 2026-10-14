import cv2
import numpy as np
import matplotlib.pyplot as plt
import os

def ausgabe_konturpunkte(approx):
    print("Approximierte Konturpunkte:")
    for i, point in enumerate(approx):
        x, y = point[0]
        print(f"Punkt {i+1}: ({x}, {y})")
    # Bilder für Anzeige vorbereiten
    original_view = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    contour_view = np.zeros_like(original_view)
    approx_view = np.zeros_like(original_view)

    # Originalkontur zeichnen
    cv2.drawContours(
        contour_view,
        [cnt],
        -1,
        (255, 0, 255),
        2
    )

    # Approximierte Kontur zeichnen
    cv2.drawContours(
        approx_view,
        [approx],
        -1,
        (0, 255, 0),
        2
    )

    # Anzeige mit matplotlib
    plt.figure(figsize=(12, 4))

    plt.subplot(1, 3, 1)
    plt.imshow(binary, cmap="gray")
    plt.title("Original")
    plt.axis("off")

    plt.subplot(1, 3, 2)
    plt.imshow(cv2.cvtColor(contour_view, cv2.COLOR_BGR2RGB))
    plt.title("Contour")
    plt.axis("off")

    plt.subplot(1, 3, 3)
    plt.imshow(cv2.cvtColor(approx_view, cv2.COLOR_BGR2RGB))
    plt.title("Approximated Contour")
    plt.axis("off")

    plt.tight_layout()
    plt.show()

    print("Anzahl Konturpunkte:", len(cnt))
    print("Anzahl approximierte Punkte:", len(approx))


# ---- Bild laden ----
# Python sucht das File im aktuellen Arbeitsordner, 
# nicht unbedingt im Ordner des Skripts.
# ==> In den Arbeitsordner wechseln 
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
img = cv2.imread("dreieck.png", cv2.IMREAD_GRAYSCALE)

# Falls kein Bild vorhanden ist: Testobjekt erzeugen
if img is None:
    img = np.zeros((300, 300), dtype=np.uint8)

    pts = np.array([
        [70, 70],
        [230, 65],
        [225, 230],
        [75, 225]
    ], np.int32)

    cv2.fillPoly(img, [pts], 255)

    # etwas Unregelmäßigkeit simulieren
    noise = np.random.randint(-5, 6, pts.shape)
    pts_noisy = pts + noise

# Binärbild erzeugen
_, binary = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)

# Konturen finden
contours, _ = cv2.findContours(
    binary,
    cv2.RETR_EXTERNAL,
    cv2.CHAIN_APPROX_SIMPLE
)

# Größte Kontur auswählen
cnt = max(contours, key=cv2.contourArea)

# Kontur approximieren
epsilon = 0.04 * cv2.arcLength(cnt, True)  # arcLength berechnet den Umfang.
# => die Vereinfachung ist unabhängig von der Objektgröße immer gleich stark
approx = cv2.approxPolyDP(cnt, epsilon, True)
ausgabe_konturpunkte(approx)

# Nur wenn tatsächlich ein Dreieck erkannt wurde
# print(("Anzahl approximierte Punkte:", len(approx)))
if len(approx) == 3:
    #  Eckpunkte in ein (3 x 2)-Array umwandeln
    pts = approx.reshape(3, 2)
    max_length = 0
    longest_edge = None

    # Alle drei Seiten untersuchen
    for i in range(3):
        p1 = pts[i]
        p2 = pts[(i + 1) % 3]

        # Seitenlänge berechnen
        length = np.linalg.norm(p2 - p1)
        print(f"Seite {i+1}: {length:.1f} Pixel")

        if length > max_length:
            max_length = length
            longest_edge = (p1, p2)

    print(f"Längste Seite: {max_length:.1f} Pixel")

# ===============================
# Dreieck mit längster Seite darstellen
# ===============================
triangle_view = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

# Dreieck grün zeichnen
cv2.drawContours(
    triangle_view,
    [approx],
    -1,
    (0,255,0),
    2
)

# Eckpunkte rot markieren
for p in pts:
    cv2.circle(
        triangle_view,
        tuple(p),
        5,
        (0,0,255),
        -1
    )

# Längste Seite blau
p1, p2 = longest_edge

cv2.line(
    triangle_view,
    tuple(p1),
    tuple(p2),
    (255,0,0),
    3
)

# Mittelpunkt der längsten Seite
mx = int((p1[0]+p2[0])/2)
my = int((p1[1]+p2[1])/2)

cv2.circle(
    triangle_view,
    (mx,my),
    5,
    (255,255,0),
    -1
)

# Winkel berechnen
dx = p2[0]-p1[0]
dy = p2[1]-p1[1]

angle = np.degrees(np.arctan2(dy,dx))

cv2.putText(
    triangle_view,
    f"{angle:.1f} deg",
    (mx+10,my),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.7,
    (255,255,255),
    2
)

# Ausgabe
plt.figure(figsize=(6,6))
plt.imshow(cv2.cvtColor(triangle_view,cv2.COLOR_BGR2RGB))
plt.title("Dreieck mit längster Seite")
plt.axis("off")
plt.show()
  
