# Tested by OJ am 12.11.24

import cv2  as cv # pip install opencv-python
import time



print("Lese alle 2 sec ein Bild von Kamera und speichere als Datei. Beenden mit <q> ")
# initialisiere WebCam
# Open the default camera  # cam = cv2.VideoCapture(0)  => dauert laneg beim Start
CAMERA_INDEX = 0
cam = cv.VideoCapture(CAMERA_INDEX, cv.CAP_DSHOW) 
# cv.CAP_DSHOW => dauert nicht so lange bis Bild von USB-Kamera kommt
print("Kamera initialisiert")

# Get the default frame width and height
frame_width = int(cam.get(cv.CAP_PROP_FRAME_WIDTH))
frame_height = int(cam.get(cv.CAP_PROP_FRAME_HEIGHT))

print("Width: {}  Height: {}".format(frame_width, frame_height))

# Define the codec and create VideoWriter object
#fourcc = cv.VideoWriter_fourcc(*'mp4v')
#out = cv.VideoWriter('output.mp4', fourcc, 20.0, (frame_width, frame_height))


# Using cv2.imwrite() method
# Saving the image
cv.imwrite(filename, img)

while True:
    ret, frame = cam.read()

    # Write the frame to the output file
    out.write(frame)

    # Display the captured frame
    cv.imshow('Camera', frame)

    # speichere das Bild ab Filename
    filename = 'foto01.jpg'
    cv.imwrite(filename, frame)

    # Press 'q' to exit the loop
    if cv.waitKey(1) == ord('q'):
        break    
    time.sleep(2)

# Release the capture and writer objects
cam.release()
#out.release()
cv.destroyAllWindows()