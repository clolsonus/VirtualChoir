import cv2
import numpy as np
import random

face_cascade = cv2.CascadeClassifier('/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml')
    
class FaceDetect():
    min_count = 10
    interval = 10
    
    def __init__(self):
        self.x = 0
        self.y = 0
        self.w = 0
        self.h = 0
        self.count = 0
        self.sumx = 0
        self.sumy = 0
        self.sumw = 0
        self.sumh = 0
        self.miss = 0
        self.skip = random.randrange(self.interval)
        self.precomputed = False

    def update_average(self, x, y, w, h):
        self.count += 1
        self.sumx += x
        self.sumy += y
        self.sumw += w
        self.sumh += h
        self.x = self.sumx / self.count
        self.y = self.sumy / self.count
        self.w = self.sumw / self.count
        self.h = self.sumh / self.count
        
    def get_face(self, mode="average"):
        return(int(round(self.x)), int(round(self.y)),
               int(round(self.w)), int(round(self.h)))
        
    def find_face(self, raw_frame, time):
        if raw_frame is None:
            return None
        
        # draw filtered face box
        if self.count > 0:
            (x, y, w, h) = self.get_face()
            #print(" ", self.fx, self.fy, self.fw, self.fh)
            
        self.skip += 1
        if self.count > self.min_count:
            if self.skip % self.interval != 0:
                return None
        else:
            print("haven't found %d matches yet ..." % self.min_count)
            
        gray = cv2.cvtColor(raw_frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.2, 5, minSize=(30,30))
        biggest_index = -1
        #biggest = 0.02 * raw_frame.shape[0] * raw_frame.shape[1]
        biggest = 0
        for i, (x,y,w,h) in enumerate(faces):
            if w*h > biggest:
                biggest_index = i
                biggest = w*h
        if biggest_index >= 0:
            # current
            (x,y,w,h) = faces[biggest_index]
            raw_frame = cv2.rectangle(np.array(raw_frame), (x,y), (x+w,y+h), (255,0,0), 2)
            print(x,y,w,h)
            self.update_average(x, y, w, h)
            #self.update_filter(x, y, w, h)
        else:
            self.miss += 1
        return raw_frame
            
    def no_face(self, raw_frame):
        if not raw_frame is None:
            self.fx = 0
            self.fy = 0
            self.fh = raw_frame.shape[0]
            self.fw = raw_frame.shape[1]
