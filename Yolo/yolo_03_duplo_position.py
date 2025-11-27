# pip install opencv-python
# pip install ultralytics    
# python -m pip install ultralytics
# & C:/Users/olafj/AppData/Local/Programs/Python/Python312/python.exe -m pip install ultralytics

from ultralytics import YOLO
import cv2
import math 
import os

# initialisiere WebCam
CAMERA_INDEX = 0
cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW) 
# was  cap = cv2.VideoCapture(0)
# cv.CAP_DSHOW => dauert nicht so lange bis Bild von USB-Kamera kommt
print("Kamera initialisiert")


cap.set(3, 640)
cap.set(4, 480)

# model
# Python sucht das File im aktuellen Arbeitsordner, 
# nicht unbedingt im Ordner des Skripts.
# ==> In den Arbeitsordner wechseln 
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)


model = YOLO("./yolov8_duplo_custom9/weights/best.pt")   
# object classes
classNames = ["duplo_4_green"]
        
while True:
    success, img = cap.read()
    results = model(img, stream=True)

    # coordinates
    for r in results:
        boxes = r.boxes

        for box in boxes:
            # bounding box
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2) # convert to int values
            # put box in cam
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 255), 3)

            # get center of item
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            print("Mittelpunkt Duplo:", cx, cy)
            # Optional: zeichnen im Bild
            #cv2.circle(img, (cx, cy), 5, (0,255,0), -1)

            # confidence
            confidence = math.ceil((box.conf[0]*100))/100
            print("Confidence --->",confidence)

            # class name
            cls = int(box.cls[0])
            print("Class name -->", classNames[cls])

            # object details
            org = [x1, y1]
            font = cv2.FONT_HERSHEY_SIMPLEX
            fontScale = 1
            color = (255, 0, 0)
            thickness = 2

            cv2.putText(img, classNames[cls], org, font, fontScale, color, thickness)

    cv2.imshow('Webcam', img)
    print("- Ende Programm mit STRG+C -")
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()