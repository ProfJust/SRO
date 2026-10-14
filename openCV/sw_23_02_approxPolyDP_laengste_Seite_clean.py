import os
import cv2
import numpy as np
import matplotlib.pyplot as plt


IMAGE_NAME = "dreieck.png"
THRESHOLD_VALUE = 127
EPSILON_FACTOR = 0.04
MIN_CONTOUR_AREA = 100


def lade_bild_graustufen(dateiname: str) -> np.ndarray:
    """Laedt ein Graustufenbild. Falls es nicht existiert, wird ein Testdreieck erzeugt."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(script_dir, dateiname)

    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    if img is None:
        print(f"Bild '{dateiname}' nicht gefunden. Erzeuge Testbild.")
        img = np.zeros((300, 300), dtype=np.uint8)
        pts = np.array([[70, 70], [230, 65], [225, 230]], dtype=np.int32)
        cv2.fillPoly(img, [pts], 255)

    return img


def erstelle_binaerbild(gray: np.ndarray) -> np.ndarray:
    """Erzeugt aus dem Graustufenbild ein Schwarz-Weiss-Bild."""
    _, binary = cv2.threshold(gray, THRESHOLD_VALUE, 255, cv2.THRESH_BINARY)
    return binary


def finde_groesste_kontur(binary: np.ndarray) -> np.ndarray | None:
    """Sucht alle Konturen und gibt die groesste Kontur zurueck."""
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    cnt = max(contours, key=cv2.contourArea)

    if cv2.contourArea(cnt) < MIN_CONTOUR_AREA:
        return None

    return cnt


def approximiere_kontur(cnt: np.ndarray) -> np.ndarray:
    """Vereinfacht die Kontur mit approxPolyDP."""
    umfang = cv2.arcLength(cnt, True)
    epsilon = EPSILON_FACTOR * umfang
    approx = cv2.approxPolyDP(cnt, epsilon, True)
    return approx


def gib_konturpunkte_aus(approx: np.ndarray) -> None:
    """Gibt die approximierten Eckpunkte auf der Konsole aus."""
    print("Approximierte Konturpunkte:")

    for i, point in enumerate(approx):
        x, y = point[0]
        print(f"Punkt {i + 1}: ({x}, {y})")

    print(f"Anzahl approximierte Punkte: {len(approx)}")


def finde_laengste_seite(approx: np.ndarray):
    """
    Bestimmt die laengste Seite der approximierten Kontur.

    Rueckgabe:
        p1, p2, max_length, angle_deg
    """
    pts = approx.reshape(-1, 2)

    if len(pts) < 3:
        raise ValueError("Die Kontur hat weniger als 3 Punkte.")

    max_length = 0.0
    longest_edge = None

    for i in range(len(pts)):
        p1 = pts[i]
        p2 = pts[(i + 1) % len(pts)]
        length = np.linalg.norm(p2 - p1)

        print(f"Seite {i + 1}: {length:.1f} Pixel")

        if length > max_length:
            max_length = length
            longest_edge = (p1, p2)

    p1, p2 = longest_edge
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    angle_deg = np.degrees(np.arctan2(dy, dx))

    print(f"Laengste Seite: {max_length:.1f} Pixel")
    print(f"Winkel der laengsten Seite: {angle_deg:.1f} Grad")

    return p1, p2, max_length, angle_deg


def zeichne_ergebnis(binary: np.ndarray, cnt: np.ndarray, approx: np.ndarray, longest_edge) -> np.ndarray:
    """Zeichnet Kontur, approximiertes Polygon und laengste Seite in ein Farbbild."""
    result = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    # Originalkontur magenta
    cv2.drawContours(result, [cnt], -1, (255, 0, 255), 1)

    # approximierte Kontur gruen
    cv2.drawContours(result, [approx], -1, (0, 255, 0), 2)

    # Eckpunkte rot
    pts = approx.reshape(-1, 2)
    for p in pts:
        cv2.circle(result, tuple(p), 5, (0, 0, 255), -1)

    # laengste Seite blau
    p1, p2 = longest_edge
    cv2.line(result, tuple(p1), tuple(p2), (255, 0, 0), 3)

    # Mittelpunkt der laengsten Seite gelb
    mx = int((p1[0] + p2[0]) / 2)
    my = int((p1[1] + p2[1]) / 2)
    cv2.circle(result, (mx, my), 5, (0, 255, 255), -1)

    # Winkel der laengsten Seite
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    angle_deg = np.degrees(np.arctan2(dy, dx))

    cv2.putText(
        result,
        f"{angle_deg:.1f} deg",
        (mx + 10, my),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )

    return result


def zeige_uebersicht(binary: np.ndarray, cnt: np.ndarray, approx: np.ndarray, result: np.ndarray) -> None:
    """Zeigt Original, Kontur, approxPolyDP und Ergebnis nebeneinander."""
    contour_view = np.zeros((*binary.shape, 3), dtype=np.uint8)
    approx_view = np.zeros((*binary.shape, 3), dtype=np.uint8)

    cv2.drawContours(contour_view, [cnt], -1, (255, 0, 255), 2)
    cv2.drawContours(approx_view, [approx], -1, (0, 255, 0), 2)

    plt.figure(figsize=(14, 4))

    plt.subplot(1, 4, 1)
    plt.imshow(binary, cmap="gray")
    plt.title("Original")
    plt.axis("off")

    plt.subplot(1, 4, 2)
    plt.imshow(cv2.cvtColor(contour_view, cv2.COLOR_BGR2RGB))
    plt.title("Kontur")
    plt.axis("off")

    plt.subplot(1, 4, 3)
    plt.imshow(cv2.cvtColor(approx_view, cv2.COLOR_BGR2RGB))
    plt.title("approxPolyDP")
    plt.axis("off")

    plt.subplot(1, 4, 4)
    plt.imshow(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
    plt.title("Laengste Seite")
    plt.axis("off")

    plt.tight_layout()
    plt.show()


def main():
    gray = lade_bild_graustufen(IMAGE_NAME)
    binary = erstelle_binaerbild(gray)

    cnt = finde_groesste_kontur(binary)
    if cnt is None:
        print("Keine passende Kontur gefunden.")
        return

    approx = approximiere_kontur(cnt)
    gib_konturpunkte_aus(approx)
    print(f"Anzahl Konturpunkte: {len(cnt)}")

    if len(approx) != 3:
        print("Warnung: Die approximierte Kontur hat nicht exakt 3 Punkte.")
        print("Die laengste Seite wird trotzdem aus dem approximierten Polygon bestimmt.")

    p1, p2, _, _ = finde_laengste_seite(approx)
    result = zeichne_ergebnis(binary, cnt, approx, (p1, p2))
    zeige_uebersicht(binary, cnt, approx, result)


if __name__ == "__main__":
    main()
