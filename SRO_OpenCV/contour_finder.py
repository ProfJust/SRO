import argparse
import cv2
import numpy as np
import sys
from typing import Tuple, List


def binarize(img_gray: np.ndarray, invert: bool) -> np.ndarray:
    # Otsu-Schwellenwert – robust bei Helligkeitsschwankungen
    _, th = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if invert:
        th = cv2.bitwise_not(th)
    # Kleine Löcher schließen & Rauschen reduzieren
    kernel = np.ones((3, 3), np.uint8)
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel, iterations=1)
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel, iterations=1)
    return th

def contour_center(cnt: np.ndarray) -> Tuple[int, int]:
    # Schwerpunkt über Momente
    M = cv2.moments(cnt)
    if M["m00"] != 0:
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        return cx, cy
    # Fallback: Mittelwert der Konturpunkte
    pts = cnt.reshape(-1, 2)
    cx, cy = pts.mean(axis=0)
    return int(cx), int(cy)

def find_contours(mask: np.ndarray) -> List[np.ndarray]:
    # cv2.findContours: unterschiedliche Rückgabe je nach OpenCV-Version
    found = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = found[0] if len(found) == 2 else found[1]
    return contours

def draw_results(bgr: np.ndarray, contours: List[np.ndarray], all_objects: bool) -> Tuple[np.ndarray, List[Tuple[int,int,int]]]:
    """
    Zeichnet Kontur(en) und Zentren.
    Returns: (Bild, Liste[(index, cx, cy)])
    """
    out = bgr.copy()
    centers = []

    if not contours:
        return out, centers

    if all_objects:
        cnts = sorted(contours, key=cv2.contourArea, reverse=True)
    else:
        cnts = [max(contours, key=cv2.contourArea)]

    for idx, cnt in enumerate(cnts, start=1):
        area = cv2.contourArea(cnt)
        if area < 5:  # ignoriere Mini-Rauschen
            continue
        cx, cy = contour_center(cnt)
        # Kontur zeichnen (grün)
        cv2.drawContours(out, [cnt], -1, (0, 255, 0), 2)
        # Schwerpunkt zeichnen (rot)
        cv2.circle(out, (cx, cy), 4, (0, 0, 255), -1)
        # kleine Beschriftung
        cv2.putText(out, f"{idx}:({cx},{cy})", (cx + 6, cy - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50, 50, 255), 1, cv2.LINE_AA)
        centers.append((idx, cx, cy))
    return out, centers

def main():
    ap = argparse.ArgumentParser(description="Kontur und Zentrum in SW-Bildern mit OpenCV")
    ap.add_argument("-i", "--image", required=True, help="Pfad zum SW-Bild (PNG/JPG)")
    ap.add_argument("-o", "--output", default=None, help="Pfad zum Speichern des Ergebnisbilds")
    ap.add_argument("--invert", action="store_true",
                    help="Setzen, wenn das Objekt dunkler als der Hintergrund ist (schwarz auf weiß)")
    ap.add_argument("--all", action="store_true",
                    help="Alle gefundenen Objekte markieren (statt nur größtes)")
    ap.add_argument("--no-show", action="store_true",
                    help="Keine Fenster anzeigen (nur Konsole/Datei-Ausgabe)")
    args = ap.parse_args()

    img = cv2.imread(args.image, cv2.IMREAD_UNCHANGED)
    if img is None:
        print("Fehler: Bild konnte nicht geladen werden.", file=sys.stderr)
        sys.exit(1)

    # In Graustufen wandeln, falls noch nicht
    if img.ndim == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        bgr = img
    else:
        gray = img
        bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    mask = binarize(gray, args.invert)
    contours = find_contours(mask)
    out, centers = draw_results(bgr, contours, args.all)

    if not centers:
        print("Kein Objekt gefunden.")
    else:
        if args.all:
            print("Zentren (Index: x, y):")
            for idx, cx, cy in centers:
                print(f"{idx}: {cx}, {cy}")
        else:
            idx, cx, cy = centers[0]
            print(f"Zentrum: {cx}, {cy}")

    if args.output:
        cv2.imwrite(args.output, out)

    if not args.no_show:
        cv2.imshow("Eingang (grau)", gray)
        cv2.imshow("Maske (binär)", mask)
        cv2.imshow("Ergebnis (Kontur + Zentrum)", out)
        print("Fenster schließen mit Taste [q] oder [ESC].")
        while True:
            key = cv2.waitKey(0) & 0xFF
            if key in (27, ord('q')):
                break
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
