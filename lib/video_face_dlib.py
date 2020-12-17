import cv2
import dlib
import math
import numpy as np
import random

class FaceDetect():
    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(4,4))
    min_count = 10
    interval = 10
    
    def __init__(self):
        self.l = 0
        self.r = 0
        self.t = 0
        self.b = 0
        self.count = 0
        self.suml = 0
        self.sumr = 0
        self.sumt = 0
        self.sumb = 0
        self.miss = 0
        self.skip = random.randrange(self.interval)
        self.precomputed = False

    def update_average(self, l, r, t, b, scale=1.0):
        self.count += 1
        self.suml += (l / scale)
        self.sumr += (r / scale)
        self.sumt += (t / scale)
        self.sumb += (b / scale)
        self.l = self.suml / self.count
        self.r = self.sumr / self.count
        self.t = self.sumt / self.count
        self.b = self.sumb / self.count
        
    def get_face(self):
        return(int(round(self.l)), int(round(self.r)),
               int(round(self.t)), int(round(self.b)))
        
    def find_face(self, raw_frame):
        if raw_frame is None:
            return None
        
        self.skip += 1
        if self.skip % self.interval != 0:
            return None
        
        if self.count < self.min_count:
            print("haven't found %d matches yet ..." % self.min_count)

        # shrink the frame if bigger than target area
        #target_area = 1138*640
        target_area = 853*480
        area = raw_frame.shape[0] * raw_frame.shape[1]
        #print("area:", area, "target_area:", target_area)
        if area > target_area:
            scale = math.sqrt( target_area / area )
            frame = cv2.resize(raw_frame, (0,0), fx=scale, fy=scale,
                               interpolation=cv2.INTER_AREA)
        else:
            scale = 1
            frame = raw_frame.copy()
            
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        detector = dlib.get_frontal_face_detector()
        detections = detector(rgb, 1)
        # print("detections:", detections)
        for r in detections:
            #print(r, type(r))
            tl = r.tl_corner()
            br = r.br_corner()
            #print(tl, type(tl))

        for rect in detections:
            l = rect.left()
            r = rect.right()
            t = rect.top()
            b = rect.bottom()
            frame = cv2.rectangle(np.array(frame), (l, t), (r, b),
                                  (128,128,255), 2)
        cv2.imshow('detections', frame)
            
        if len(detections):
            l = detections[0].left()
            r = detections[0].right()
            t = detections[0].top()
            b = detections[0].bottom()
            for rect in detections[1:]:
                if rect.left() < l:
                    l = rect.left()
                if rect.right() > r:
                    r = rect.right()
                if rect.top() < t:
                    t = rect.top()
                if rect.bottom() > b:
                    b = rect.bottom()
            self.update_average(l, r, t, b, scale)
        else:
            self.miss += 1

        (l, r, t, b) = self.get_face()
        raw_frame = cv2.rectangle(np.array(raw_frame), (l, t), (r, b), (255,255,255), 2)
        return raw_frame
            
    def no_face(self, raw_frame):
        if not raw_frame is None:
            self.x = 0
            self.y = 0
            self.h = raw_frame.shape[0]
            self.w = raw_frame.shape[1]
