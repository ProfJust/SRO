import cv2
img = cv2.imread('foto01.jpg',cv2.IMREAD_GRAYSCALE)
edge = cv2.Canny(img, 50, 200)
cv2.imshow('Bild', edge)
cv2.waitKey(0)
cv2.destroyAllWindows()
