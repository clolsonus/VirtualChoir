import cv2
import dlib
import math
import matplotlib.pyplot as plt
import numpy as np
import random

def gen_func( coeffs, min, max, steps ):
    if abs(max-min) < 0.0001:
        max = min + 0.1
    xvals = []
    yvals = []
    step = (max - min) / steps
    func = np.poly1d(coeffs)
    for x in np.arange(min, max+step, step):
        y = func(x)
        xvals.append(x)
        yvals.append(y)
    return xvals, yvals

class FaceDetect():
    def __init__(self):
        self.data = []
        self.count = 0
        self.miss = 0
        self.left_func = None
        self.right_func = None
        self.top_func = None
        self.bottom_func = None
        
    def data_append(self, time, l, r, t, b, scale=1.0):
        self.count += 1
        record = {
            "time": time, 
            "left": l / scale, "right": r / scale,
            "top": t / scale, "bottom": b / scale,
            "count": self.count, "miss": self.miss
        }
        self.data.append( record )

    def update_interp(self):
        degree = 2
        self.count = len(self.data)
        if self.count <= degree:
            return
        time = []
        left = []
        right = []
        top = []
        bottom = []
        for record in self.data:
            time.append(record["time"])
            left.append(record["left"])
            right.append(record["right"])
            top.append(record["top"])
            bottom.append(record["bottom"])
        left_fit, res, _, _, _ = np.polyfit( time, left, degree, full=True )
        self.left_func = np.poly1d(left_fit)
        #print("left fit:", left_fit)
        #print("left res:", res)
        xvals, yvals = gen_func(left_fit,time[0], time[-1], 1000)
        plt.scatter(time, left, marker='*', label="Left")
        plt.plot(xvals, yvals, label="Left Fit")
        right_fit, res, _, _, _ = np.polyfit( time, right, degree, full=True )
        self.right_func = np.poly1d(right_fit)
        #xvals, yvals = gen_func(right_fit,time[0], time[-1], 1000)
        #plt.scatter(time, right, marker='*', label="Right")
        #plt.plot(xvals, yvals, label="Right Fit")
        top_fit, res, _, _, _ = np.polyfit( time, top, degree, full=True )
        self.top_func = np.poly1d(top_fit)
        #xvals, yvals = gen_func(top_fit,time[0], time[-1], 1000)
        #plt.scatter(time, top, marker='*', label="Top")
        #plt.plot(xvals, yvals, label="Top Fit")
        bottom_fit, res, _, _, _ = np.polyfit( time, bottom, degree, full=True )
        self.bottom_func = np.poly1d(bottom_fit)
        #xvals, yvals = gen_func(bottom_fit,time[0], time[-1], 1000)
        #plt.scatter(time, bottom, marker='*', label="Bottom")
        #plt.plot(xvals, yvals, label="Bottom Fit")
        #plt.legend()
        #plt.show()
        
    def get_face(self, time, scale=1.0):
        if self.left_func is None or self.right_func is None or self.top_func is None or self.bottom_func is None:
            return None
        l = self.left_func(time)*scale
        r = self.right_func(time)*scale
        t = self.top_func(time)*scale
        b = self.bottom_func(time)*scale
        return l, r, t, b
        
    def find_face(self, raw_frame, time):
        if raw_frame is None:
            return None
        
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
            self.data_append(time, l, r, t, b, scale)
        else:
            self.miss += 1
            return None

        self.update_interp()
        result = self.get_face(time, scale)
        if not result is None:
            (l, r, t, b) = result
            frame = cv2.rectangle(np.array(frame), (int(l), int(t)), (int(r), int(b)), (255,255,255), 2)
        
        cv2.imshow('face detection', frame)
        cv2.waitKey(1)

        return (l, r, t, b)
