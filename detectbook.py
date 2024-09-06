import cv2
import numpy as np


class Opencamera:

    def __init__(self):
        self.camera = cv2.VideoCapture(1)

    def open(self):
        while True:
            rat,frame =self.camera.read()
            cv2.imshow("camera",frame)

            if cv2.waitKey(1)  & 0xFF== ord("q"):
                break

        self.camera.release()
        cv2.destroyWindow("camera")


# if __name__ == "__main__":
#     opencamera = Opencamera()
#     opencamera.open()