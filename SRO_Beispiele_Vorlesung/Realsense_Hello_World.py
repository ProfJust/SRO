import pyrealsense2 as rs

try:
    # Pipeline initialisieren
    pipeline = rs.pipeline()

    # Pipeline starten (automatische Gerätesuche und Standard-Streams)
    pipeline.start()

    while True:
        # Frames abwarten
        frames = pipeline.wait_for_frames()
        # Tiefenbild extrahieren
        depth_frame = frames.get_depth_frame()
        if not depth_frame:
            continue

        # Breite und Höhe
        width = depth_frame.get_width()
        height = depth_frame.get_height()

        # Abstand zum Objekt im Bildzentrum (in Metern)
        dist_to_center = depth_frame.get_distance(width // 2, height // 2)

        print(f"The camera is facing an object {dist_to_center:.3f} meters away", end="\r")

except rs.error as e:
    print(f"RealSense error calling {e.get_failed_function()}({e.get_failed_args()}):\n    {e}")
except Exception as e:
    print(e)
