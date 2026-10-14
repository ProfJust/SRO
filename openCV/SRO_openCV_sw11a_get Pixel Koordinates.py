# SRO_openCV_sw11_pixel2worldCoordinates.py
# ................................
# Tested by OJ am 16.3.26 
# python 3.12.7
# WebCam anschliessen => Bildkoordinaten (u,v) in Pixeln
# in reale Tischkoordinaten (x,y) in mm umrechnen
# -------------------------------------

import cv2

WINDOW_NAME = "Webcam mit Fadenkreuz"


class CrosshairViewer:
    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.cap = None

        self.cross_x = None
        self.cross_y = None

        self.frame_width = 0
        self.frame_height = 0

    def open_camera(self):
        self.cap = cv2.VideoCapture(self.camera_index)

        if not self.cap.isOpened():
            raise RuntimeError("Webcam konnte nicht geöffnet werden.")

        ok, frame = self.cap.read()
        if not ok or frame is None:
            raise RuntimeError("Es konnte kein Bild von der Webcam gelesen werden.")

        self.frame_height, self.frame_width = frame.shape[:2]

        # Startposition des Fadenkreuzes in der Bildmitte
        self.cross_x = self.frame_width // 2
        self.cross_y = self.frame_height // 2

    def close_camera(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def mouse_callback(self, event, x, y, flags, param):
        # Linksklick setzt das Fadenkreuz
        if event == cv2.EVENT_LBUTTONDOWN:
            self.cross_x = x
            self.cross_y = y
            print(f"Gewählter Pixel: x={x}, y={y}")

        # Optional: Mit gedrückter linker Maustaste ziehen
        elif event == cv2.EVENT_MOUSEMOVE and (flags & cv2.EVENT_FLAG_LBUTTON):
            self.cross_x = x
            self.cross_y = y

    def draw_crosshair(self, frame):
        if self.cross_x is None or self.cross_y is None:
            return frame

        x = int(self.cross_x)
        y = int(self.cross_y)

        h, w = frame.shape[:2]

        # Horizontale Linie
        cv2.line(frame, (0, y), (w - 1, y), (0, 255, 0), 1)

        # Vertikale Linie
        cv2.line(frame, (x, 0), (x, h - 1), (0, 255, 0), 1)

        # Mittelpunkt hervorheben
        cv2.circle(frame, (x, y), 5, (0, 0, 255), 2)

        # Koordinaten anzeigen
        text = f"x={x}, y={y}"
        text_x = min(x + 10, w - 180)
        text_y = max(y - 10, 25)

        cv2.rectangle(
            frame,
            (text_x - 5, text_y - 20),
            (text_x + 140, text_y + 5),
            (0, 0, 0),
            -1
        )
        cv2.putText(
            frame,
            text,
            (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2,
            cv2.LINE_AA
        )

        return frame

    def run(self):
        self.open_camera()

        cv2.namedWindow(WINDOW_NAME)
        cv2.setMouseCallback(WINDOW_NAME, self.mouse_callback)

        try:
            while True:
                ok, frame = self.cap.read()
                if not ok or frame is None:
                    print("Warnung: Kamerabild konnte nicht gelesen werden.")
                    break

                frame = self.draw_crosshair(frame)

                # Zusätzliche Info unten links
                help_text = "Linksklick: Fadenkreuz setzen | q oder ESC: Beenden"
                cv2.putText(
                    frame,
                    help_text,
                    (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA
                )

                cv2.imshow(WINDOW_NAME, frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q") or key == 27:  # q oder ESC
                    break

        finally:
            self.close_camera()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    app = CrosshairViewer(camera_index=1)  # Kamera-Index anpassen, falls nötig beim Laptop = 1 
    app.run()