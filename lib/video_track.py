import cv2
import skvideo.io               # pip install sk-video

from .logger import log

class VideoTrack:
    def __init__(self):
        self.reader = None
        self.place_x = None
        self.place_y = None
        self.size_w = 0
        self.size_h = 0
        self.sort_order = 999999
        self.frame = []
        self.raw_frame = None
        self.shaped_frame = None

    def open(self, file):
        print("video:", file)
        metadata = skvideo.io.ffprobe(file)
        #print(metadata.keys())
        if not "video" in metadata:
            print("no video track")
            return False
        #print(json.dumps(metadata["video"], indent=4))
        fps_string = metadata['video']['@r_frame_rate']
        (num, den) = fps_string.split('/')
        self.fps = float(num) / float(den)
        if self.fps < 1 or self.fps > 120:
            # something crazy happened let's try something else
            fps_string = metadata['video']['@avg_frame_rate']
            (num, den) = fps_string.split('/')
            self.fps = float(num) / float(den)

        self.fps = float(num) / float(den)
        codec = metadata['video']['@codec_long_name']
        self.w = int(metadata['video']['@width'])
        self.h = int(metadata['video']['@height'])
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

    def get_frame(self, time, rotate=0):
        # return the frame closest to the requested time
        frame_num = int(round(time * self.fps))
        # print("request frame num:", frame_num)
        if frame_num < 0:
            self.raw_frame = None
            return
        while self.frame_counter < frame_num and not self.frame is None:
            try:
                self.frame = self.reader._readFrame()
                self.frame = self.frame[:,:,::-1]
                self.frame_counter += 1
                if not len(self.frame):
                    self.frame = None
            except:
                self.frame = None
                
        if self.frame is not None:
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
        else:
            # no more frames, impliment a simple fade out
            if self.raw_frame is not None:
                self.raw_frame = (self.raw_frame * 0.9).astype('uint8')

    def skip_secs(self, seconds):
        if not self.reader:
            return
        skip_frames = int(round( seconds * self.fps ))
        print("skipping first %.2f seconds (%d frames.)" % (seconds, skip_frames))
        for i in range(skip_frames):
            self.reader._readFrame()

    def next_frame(self):
        try:
            frame = self.reader._readFrame()
        except:
            return None
        if not len(frame):
            return None
        frame = frame[:,:,::-1]     # convert from RGB to BGR (to make opencv happy)
        return frame

