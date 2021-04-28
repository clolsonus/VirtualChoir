import cv2
import json
import os
import skvideo.io               # pip install sk-video

from .logger import log
from .video_face_dlib import FaceDetect

class VideoTrack:
    def __init__(self):
        self.file = None
        self.reader = None
        self.displayw = None
        self.place_x = None
        self.place_y = None
        self.size_w = 0
        self.size_h = 0
        self.sort_order = 999999
        self.frame = []
        self.raw_frame = None
        self.shaped_frame = None
        self.face = FaceDetect()
        self.local_time = 0.0

    def open(self, file):
        self.file = file
        print("video:", file)
        metadata = skvideo.io.ffprobe(file)
        #print(metadata.keys())
        if not "video" in metadata:
            log("No video track:", file)
            return False
        print(json.dumps(metadata["video"], indent=4))
        fps_string = metadata['video']['@r_frame_rate']
        (num, den) = fps_string.split('/')
        self.fps = float(num) / float(den)
        # sanity check fps
        use_backup_fps = False
        name, ext = os.path.splitext(file)
        # catch bogus frame per second attributes
        if ext[1:] == "webm" and (self.fps < 1 or self.fps > 1000):
            use_backup_fps = True
        elif self.fps < 1 or self.fps > 240:
            use_backup_fps = True
        # get avg fps
        fps_string = metadata['video']['@avg_frame_rate']
        (num, den) = fps_string.split('/')
        if float(den) > 0:
            avg_fps = float(num) / float(den)
        else:
            avg_fps = 0
        # check for consensus with reported frame rate
        #if avg_fps > 0:
        #    ratio = self.fps / avg_fps
        #    if ratio < 0.9 or ratio > 1.1:
        #        # disagreement with self reported fps
        #        use_backup_fps = True
        if avg_fps > 0 and use_backup_fps:
            # something crazy happened let's try the average fps
            self.fps = avg_fps
        if self.fps > 10000:
            # just, nope.
            self.fps = 30 # this will bite me later
        codec = metadata['video']['@codec_long_name']
        self.w = int(metadata['video']['@width'])
        self.h = int(metadata['video']['@height'])
        if '@sample_aspect_ratio' in metadata['video']:
            num, den = metadata['video']['@sample_aspect_ratio'].split(':')
            if int(den) > 0:
                width_mul = int(num) / int(den)
            else:
                width_mul = 1
            if width_mul < 0.8 or width_mul > 1.2:
                self.displayw = int(round(self.w * width_mul))
                self.w = self.displayw
        if '@duration' in metadata['video']:
            self.duration = float(metadata['video']['@duration'])
        else:
            self.duration = 1
        self.total_frames = int(round(self.duration * self.fps))
        self.frame_counter = -1

        print('fps:', self.fps)
        print('codec:', codec)
        print('output size:', self.w, 'x', self.h)
        print('total frames:', self.total_frames)

        print("Opening ", file)
        self.reader = skvideo.io.FFmpegReader(file, inputdict={}, outputdict={})
        self.get_frame(0.0)     # read first frame
        if self.frame is None:
            log("warning: no first frame in:", file)
        return True

    def get_frame(self, local_time, rotate=0):
        # return the frame closest to the requested time
        frame_num = int(round(local_time * self.fps))
        if frame_num < 0:
            self.raw_frame = None
            self.local_time = 0.0
            return
        while self.frame_counter < frame_num and not self.frame is None:
            try:
                self.frame = self.reader._readFrame()
                self.frame = self.frame[:,:,::-1]
                if not self.displayw is None:
                    self.frame = cv2.resize(self.frame, (self.displayw, self.h),
                                            interpolation=cv2.INTER_AREA)
                self.local_time = local_time
                self.frame_counter += 1
                if not len(self.frame):
                    self.frame = None
                #else:
            except:
                self.frame = None
        if self.frame is not None:
            #cv2.imshow("before", self.frame)
            if rotate == 0:
                self.raw_frame = self.frame
            elif rotate == 90:
                tmp = cv2.transpose(self.frame)
                self.raw_frame = cv2.flip(tmp, 1)
            elif rotate == 180:
                self.raw_frame = cv2.flip(self.frame, -1)
            elif rotate == 270:
                tmp = cv2.transpose(self.frame)
                self.raw_frame = cv2.flip(tmp, 0)
            else:
                print("unhandled rotation angle:", rotate)
            #cv2.imshow("after", self.raw_frame)
        else:
            # no more frames, impliment a simple fade out
            if self.raw_frame is not None:
                self.raw_frame = (self.raw_frame * 0.9).astype('uint8')

    def find_face(self):
        result = self.face.find_face(self.raw_frame)
        if not result is None:
            self.raw_frame = result
        
    def no_face(self):
        self.face.no_face(self.raw_frame)
        
    def skip_secs(self, seconds):
        if not self.reader:
            return
        skip_frames = int(round( seconds * self.fps ))
        print("skipping first %.2f seconds (%d frames.)" % (seconds, skip_frames))
        for i in range(skip_frames):
            self.reader._readFrame()

    # deprecated?
    def next_frame(self):
        try:
            frame = self.reader._readFrame()
        except:
            return None
        if not len(frame):
            return None
        frame = frame[:,:,::-1]     # convert from RGB to BGR (to make opencv happy)
        return frame

