# https://github.com/IntelRealSense/librealsense/tree/master/examples/hello-realsense
import pyrealsense2 as rs
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="Hello RealSense example demonstrates the basics of connecting to a RealSense device and taking advantage of depth data.")
    args = parser.parse_args()

    try:
        # Create a pipeline - this serves as a top-level API for streaming and processing frames
        pipeline = rs.pipeline()

        # Configure and start the pipeline
        pipeline.start()

        try:
            while True:
                # Wait for a coherent pair of frames: depth and color
                frames = pipeline.wait_for_frames()
                depth_frame = frames.get_depth_frame()

                if not depth_frame:
                    continue

                # Get the depth frame's dimensions
                width = depth_frame.get_width()
                height = depth_frame.get_height()

                # Query the distance from the camera to the object in the center of the image
                dist_to_center = depth_frame.get_distance(width // 2, height // 2)

                # Print the distance
                print(f"The camera is facing an object {dist_to_center:.2f} meters away \r", end="", flush=True)

        finally:
            # Stop streaming
            pipeline.stop()

    except rs.error as e:
        print(f"RealSense error calling {e.get_failed_function()} ({e.get_failed_args()}):\n    {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
