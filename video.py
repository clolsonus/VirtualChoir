import cv2
import json
import skvideo.io               # pip install sk-video

class VideoTrack:
    def __init__(self):
        self.reader = None

    def open(self, file):
        metadata = skvideo.io.ffprobe(file)
        #print(metadata.keys())
        #print(json.dumps(metadata["video"], indent=4))
        fps_string = metadata['video']['@avg_frame_rate']
        (num, den) = fps_string.split('/')
        self.fps = float(num) / float(den)
        codec = metadata['video']['@codec_long_name']
        self.w = int(metadata['video']['@width'])
        self.h = int(metadata['video']['@height'])
        self.total_frames = int(round(float(metadata['video']['@duration']) * self.fps))

        print('fps:', self.fps)
        print('codec:', codec)
        print('output size:', self.w, 'x', self.h)
        print('total frames:', self.total_frames)

        print("Opening ", file)
        self.reader = skvideo.io.FFmpegReader(file, inputdict={}, outputdict={})

    def skip_secs(self, seconds):
        skip_frames = int(round( seconds * self.fps ))
        print("skipping first %d frames." % skip_frames)
        for i in range(skip_frames):
            print(" skipping:", i)
            self.reader._readFrame()

    def next_frame(self):
        try:
            frame = self.reader._readFrame()
        except:
            return None
        frame = frame[:,:,::-1]     # convert from RGB to BGR (to make opencv happy)
        return frame
