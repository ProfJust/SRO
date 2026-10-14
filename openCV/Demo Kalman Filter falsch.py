import cv2
import numpy as np
import matplotlib.pyplot as plt


def create_triangle_image(angle_deg=25, size=400):
    img = np.zeros((size, size), dtype=np.uint8)

    pts = np.array([
        [-80, 60],
        [80, 60],
        [0, -90]
    ], dtype=np.float32)

    angle_rad = np.deg2rad(angle_deg)
    R = np.array([
        [np.cos(angle_rad), -np.sin(angle_rad)],
        [np.sin(angle_rad),  np.cos(angle_rad)]
    ])

    pts_rot = pts @ R.T
    pts_rot += np.array([size // 2, size // 2])
    pts_rot = pts_rot.astype(np.int32)

    cv2.fillPoly(img, [pts_rot], 255)
    return img


def add_noise(img, noise_level=35):
    noise = np.random.normal(0, noise_level, img.shape).astype(np.int16)
    noisy = img.astype(np.int16) + noise
    noisy = np.clip(noisy, 0, 255).astype(np.uint8)
    return noisy


def measure_angle(img):
    _, binary = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(
        binary,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        return None, binary

    cnt = max(contours, key=cv2.contourArea)

    epsilon = 0.04 * cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, epsilon, True)

    if len(approx) < 3:
        return None, binary

    pts = approx.reshape(-1, 2)

    max_length = 0
    longest_edge = None

    for i in range(len(pts)):
        p1 = pts[i]
        p2 = pts[(i + 1) % len(pts)]

        length = np.linalg.norm(p2 - p1)

        if length > max_length:
            max_length = length
            longest_edge = (p1, p2)

    p1, p2 = longest_edge

    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]

    angle = np.degrees(np.arctan2(dy, dx))

    # Winkel auf 0...180 Grad normieren
    angle = angle % 180

    return angle, binary


def create_kalman_filter():
    kalman = cv2.KalmanFilter(2, 1)

    # Zustand: [Winkel, Winkelgeschwindigkeit]
    kalman.transitionMatrix = np.array([
        [1, 1],
        [0, 1]
    ], dtype=np.float32)

    # Messung: nur Winkel
    kalman.measurementMatrix = np.array([
        [1, 0]
    ], dtype=np.float32)

    kalman.processNoiseCov = np.array([
        [1e-3, 0],
        [0, 1e-3]
    ], dtype=np.float32)

    kalman.measurementNoiseCov = np.array([
        [2.0]
    ], dtype=np.float32)

    kalman.errorCovPost = np.eye(2, dtype=np.float32)

    kalman.statePost = np.array([
        [0],
        [0]
    ], dtype=np.float32)

    return kalman


def kalman_filter_angle(kalman, measured_angle):
    measurement = np.array([[measured_angle]], dtype=np.float32)

    kalman.predict()
    corrected = kalman.correct(measurement)

    return float(corrected[0, 0])


# -------------------------------
# Hauptprogramm
# -------------------------------

true_angle = 25
num_frames = 80

kalman = create_kalman_filter()

measured_angles = []
filtered_angles = []

for i in range(num_frames):
    clean = create_triangle_image(angle_deg=true_angle)
    noisy = add_noise(clean, noise_level=45)

    measured_angle, binary = measure_angle(noisy)

    if measured_angle is None:
        continue

    filtered_angle = kalman_filter_angle(kalman, measured_angle)

    measured_angles.append(measured_angle)
    filtered_angles.append(filtered_angle)

    display = cv2.cvtColor(noisy, cv2.COLOR_GRAY2BGR)

    cv2.putText(
        display,
        f"Messung: {measured_angle:.1f} deg",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 255),
        2
    )

    cv2.putText(
        display,
        f"Kalman: {filtered_angle:.1f} deg",
        (20, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )

    cv2.imshow("Verrauschtes Bild", display)
    cv2.imshow("Binaerbild", binary)

    if cv2.waitKey(80) & 0xFF == ord("q"):
        break

cv2.destroyAllWindows()

# Ergebnis plotten
plt.figure(figsize=(10, 5))
plt.plot(measured_angles, label="Gemessener Winkel")
plt.plot(filtered_angles, label="Kalman-gefilterter Winkel")
plt.axhline(true_angle, linestyle="--", label="Wahrer Winkel")
plt.xlabel("Frame")
plt.ylabel("Winkel in Grad")
plt.title("Kalman-Filter zur Winkelglättung")
plt.legend()
plt.grid(True)
plt.show()