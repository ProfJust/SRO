# https://raw.githubusercontent.com/IntelRealSense/librealsense/refs/heads/master/examples/capture/rs-capture.cpp

import pyrealsense2 as rs
import numpy as np
import cv2
import os
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="RealSense Capture - Speichert Tiefen- und Farbbilder in Dateien.")
    parser.add_argument("--output", "-o", type=str, default="output", help="Ausgabeordner für die Bilder")
    parser.add_argument("--count", "-c", type=int, default=10, help="Anzahl der zu speichernden Bilder")
    args = parser.parse_args()

    # Ausgabeordner erstellen, falls nicht vorhanden
    os.makedirs(args.output, exist_ok=True)

    # Pipeline konfigurieren
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

    try:
        # Pipeline starten
        pipeline.start(config)

        # Warten, bis die Kamera bereit ist
        profile = pipeline.get_active_profile()
        depth_profile = rs.video_stream_profile(profile.get_stream(rs.stream.depth))
        depth_intrinsics = depth_profile.get_intrinsics()

        align_to = rs.stream.color
        align = rs.align(align_to)

        frame_count = 0
        while frame_count < args.count:
            # Frames abrufen
            frames = pipeline.wait_for_frames()
            aligned_frames = align.process(frames)
            depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()

            if not depth_frame or not color_frame:
                continue

            # Bilder in numpy arrays umwandeln
            depth_image = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())

            # Bilder speichern
            cv2.imwrite(os.path.join(args.output, f"depth_{frame_count:04d}.png"), depth_image)
            cv2.imwrite(os.path.join(args.output, f"color_{frame_count:04d}.png"), color_image)

            print(f"Gespeichert: depth_{frame_count:04d}.png, color_{frame_count:04d}.png")
            frame_count += 1

    except rs.error as e:
        print(f"RealSense-Fehler in {e.get_failed_function()} ({e.get_failed_args()}):\n    {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Fehler: {e}")
        sys.exit(1)
    finally:
        pipeline.stop()
        print("Pipeline gestoppt.")

if __name__ == "__main__":
    main()
