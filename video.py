import cv2
import json
import numpy as np
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
        print("skipping first %.1f seconds (%d frames.)" % (seconds, skip_frames))
        for i in range(skip_frames):
            self.reader._readFrame()

    def next_frame(self):
        try:
            frame = self.reader._readFrame()
        except:
            return None
        frame = frame[:,:,::-1]     # convert from RGB to BGR (to make opencv happy)
        return frame

#
# work on generating video early for testing purposes
#
# fixme: deal with different input fps
# fixme: deal with beat sync (maybe?)
# fixme: better size & arrangement scheme
# fixme: borders around frames?
def render_combined_video( video_names, offsets ):
    # open all video clips and advance to clap sync point
    videos = []
    for i, file in enumerate(video_names):
        v = VideoTrack()
        v.open(file)
        v.skip_secs(offsets[i] / 1000)
        videos.append(v)

    # stats from first video
    fps = videos[0].fps
    w = videos[0].w
    h = videos[0].h
    # open writer for output
    inputdict = {
        '-r': str(fps)
    }
    lossless = {
        # See all options: https://trac.ffmpeg.org/wiki/Encode/H.264
        '-vcodec': 'libx264',  # use the h.264 codec
        '-crf': '0',           # set the constant rate factor to 0, (lossless)
        '-preset': 'veryslow', # maximum compression
        '-r': str(fps)         # match input fps
    }
    sane = {
        # See all options: https://trac.ffmpeg.org/wiki/Encode/H.264
        '-vcodec': 'libx264',  # use the h.264 codec
        '-crf': '17',          # visually lossless (or nearly so)
        '-preset': 'medium',   # default compression
        '-r': str(fps)         # match input fps
    }
    writer = skvideo.io.FFmpegWriter("group.mp4", inputdict=inputdict, outputdict=sane)
    done = False
    while not done:
        done = True
        frames = []
        for i, v in enumerate(videos):
            frame = v.next_frame()
            if not frame is None:
                done = False
                frame_scale = cv2.resize(frame, (0,0), fx=0.25, fy=0.25,
                                 interpolation=cv2.INTER_AREA)
                frames.append(frame_scale)
                # cv2.imshow(video_names[i], frame_scale)
        if not done:
            main_frame = np.zeros(shape=[frames[0].shape[0], frames[0].shape[1]*4, frames[0].shape[2]], dtype=np.uint8)
            for i, f in enumerate(frames):
                if not f is None:
                    main_frame[0:f.shape[0],f.shape[1]*i:f.shape[1]*i+f.shape[1]] = f
            cv2.imshow("main", main_frame)
            cv2.waitKey(1)
            writer.writeFrame(main_frame[:,:,::-1])  #write the frame as RGB not BGR
    writer.close()
