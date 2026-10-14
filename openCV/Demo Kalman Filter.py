import cv2
import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------
# Einstellungen
# ---------------------------------------------------
TRUE_ANGLE = 25.0          # Wahrer Winkel
NUM_SAMPLES = 100          # Anzahl Messungen
NOISE_STD = 4.0            # Standardabweichung des Messrauschens

# ---------------------------------------------------
# Kalman-Filter erzeugen
# Zustand = [Winkel, Winkelgeschwindigkeit]
# Messung = [Winkel]
# ---------------------------------------------------

kalman = cv2.KalmanFilter(2, 1)

kalman.transitionMatrix = np.array([
    [1, 1],
    [0, 1]
], np.float32)

kalman.measurementMatrix = np.array([
    [1, 0]
], np.float32)

kalman.processNoiseCov = np.array([
    [1e-4, 0],
    [0, 1e-4]
], np.float32)

kalman.measurementNoiseCov = np.array([
    [NOISE_STD**2]
], np.float32)

kalman.errorCovPost = np.eye(2, dtype=np.float32)

# ---------------------------------------------------
# Messwerte erzeugen
# ---------------------------------------------------

measurements = TRUE_ANGLE + np.random.randn(NUM_SAMPLES) * NOISE_STD

# Kalman mit erster Messung initialisieren
kalman.statePost = np.array([
    [measurements[0]],
    [0]
], dtype=np.float32)

filtered = []

# ---------------------------------------------------
# Filter anwenden
# ---------------------------------------------------

for z in measurements:

    kalman.predict()

    estimate = kalman.correct(
        np.array([[z]], dtype=np.float32)
    )

    filtered.append(float(estimate[0, 0]))

filtered = np.array(filtered)

# ---------------------------------------------------
# Diagramm
# ---------------------------------------------------

plt.figure(figsize=(11,5))

plt.plot(measurements,
         '.-',
         label="Verrauschte Messung",
         alpha=0.7)

plt.plot(filtered,
         '-',
         linewidth=2,
         label="Kalman-Filter")

plt.axhline(TRUE_ANGLE,
            color='red',
            linestyle='--',
            linewidth=2,
            label="Wahrer Winkel")

plt.title("Kalman-Filter zur Winkelglättung")
plt.xlabel("Messung")
plt.ylabel("Winkel [°]")
plt.grid(True)
plt.legend()

plt.tight_layout()
plt.show()

# ---------------------------------------------------
# Statistik
# ---------------------------------------------------

print(f"Wahrer Winkel        : {TRUE_ANGLE:.2f}°")
print(f"Mittel Messung       : {np.mean(measurements):.2f}°")
print(f"Std Messung          : {np.std(measurements):.2f}°")
print(f"Mittel Kalman        : {np.mean(filtered):.2f}°")
print(f"Std Kalman           : {np.std(filtered):.2f}°")