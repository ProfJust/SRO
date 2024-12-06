import cv2
# ggf.  pip install imutils
import imutils

# Image path
image_path = r'C:\mySciebo\_SRO\_GitHub\SRO\SRO_OpenCV\map.pgm'
# lese Bild von Festplatte
#map = cv2.imread("map.pgm")
map = cv2.imread(image_path)
 
# warte auf Tastendruck (wichtig, sonst sieht man das Fenster nicht)
print(" Das Bild per Maus aktivieren, dann Taste drücken => Weiter")
cv2.waitKey(0)

img = map.copy()

# Displaying the result
cv2.namedWindow("Original", cv2.WINDOW_NORMAL)
cv2.imshow("Original", img)

# invert for edge detection
# https://docs.opencv.org/3.4/d0/d86/tutorial_py_image_arithmetics.html
gray = cv2.bitwise_not(img)

# Canny Edge Detection 
# https://docs.opencv.org/4.x/da/d22/tutorial_py_canny.html
# minval, maxval
edges = cv2.Canny(gray, 100, 400)
cv2.namedWindow("Edges", cv2.WINDOW_NORMAL)
cv2.imshow("Edges", edges)

# Parameter
tAprox = 3.0  # 1/10 Prozent Aproximation
tKsCav = 2.0  # Kernel Size for Caviatation
tKsDel = 2.0 # Kernel Size for Dilation

# Find the contours. 
# https://docs.opencv.org/3.4/dd/d49/tutorial_py_contour_features.html
cnts = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
# The first two largest contours are for the outer contour
# So, taking the rest of the contours for inner contours
if len(cnts) == 2:
    cnts = cnts[0]
else:
    cnts[1]

# print(cnts)
im = map.copy()
contours = cv2.drawContours(im, cnts, -1, (0,0,0),1)
# Displaying the result
cv2.namedWindow("Contours", cv2.WINDOW_NORMAL)
cv2.imshow("Contours", contours)

"""cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[2:]
# Filling the inner contours with black color

for c in cnts:
    epsilon = tAprox * cv2.arcLength(c, False)
    approx = cv2.approxPolyDP(c, epsilon, False)
    cv2.drawContours(img, [approx], -1, (0, 0, 0), -1)
    
# Displaying the result
cv2.namedWindow("Contour", cv2.WINDOW_NORMAL)
cv2.imshow("Contour", img)
"""

# Parameter
tAprox = 3.0  # 1/10 Prozent Aproximation
tKsCav = 3.0  # Größe des Morphologischen Elements
tKsDel = 3.0 # Kernel Size for Dilation

map_with_contours = cv2.addWeighted(map,0.5,contours,0.5,0.0)
# Displaying the result
cv2.namedWindow("Map with Contours", cv2.WINDOW_NORMAL)
cv2.imshow("Map with Contours", map_with_contours)


# Erosion und Dilatation
kernelCav = cv2.getStructuringElement(cv2.MORPH_RECT, (int(tKsCav), int(tKsCav)))
cavPic = cv2.erode(map_with_contours, kernelCav)

kernelDel = cv2.getStructuringElement(cv2.MORPH_RECT, (int(tKsDel), int(tKsDel)))
delPic = cv2.dilate(cavPic, kernelDel)
image = delPic.copy()
        
# Displaying the result
cv2.namedWindow("Map with contours after Erode & Dilate", cv2.WINDOW_NORMAL)
cv2.imshow("Map with contours after Erode & Dilate", image)

# Black & White (image, threshold, =>val, tresholdFunktion)
#cv2.threshold(image, 200, 0, cv2.THRESH_BINARY)
thresh = 127
im_bw = cv2.threshold(image, thresh, 255, cv2.THRESH_BINARY)[1]


cv2.namedWindow("Final", cv2.WINDOW_NORMAL)
cv2.imshow("Final", im_bw)
#print(im_bw)


# portable bitmap(.pgm) expects gray image in function 'write'
# https://docs.opencv.org/3.4/d8/d01/group__imgproc__color__conversions.html
gray_img = cv2.cvtColor(im_bw, cv2.COLOR_BGR2GRAY)
cv2.imwrite('map_improved.pgm', gray_img)


cv2.waitKey(0)
cv2.destroyAllWindows()