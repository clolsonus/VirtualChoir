import cv2
import json
import math
import numpy as np
import os
import skvideo.io               # pip install sk-video

class VideoTrack:
    def __init__(self):
        self.reader = None

    def open(self, file):
        metadata = skvideo.io.ffprobe(file)
        #print(metadata.keys())
        #print(json.dumps(metadata["video"], indent=4))
        if not "video" in metadata:
            return False
        fps_string = metadata['video']['@avg_frame_rate']
        (num, den) = fps_string.split('/')
        self.fps = float(num) / float(den)
        codec = metadata['video']['@codec_long_name']
        self.w = int(metadata['video']['@width'])
        self.h = int(metadata['video']['@height'])
        self.total_frames = int(round(float(metadata['video']['@duration']) * self.fps))
        self.frame_counter = -1
        self.frame = []

        print('fps:', self.fps)
        print('codec:', codec)
        print('output size:', self.w, 'x', self.h)
        print('total frames:', self.total_frames)

        print("Opening ", file)
        self.reader = skvideo.io.FFmpegReader(file, inputdict={}, outputdict={})
        return True

    def get_frame(self, time):
        # return the frame closest to the requested time
        frame_num = int(round(time * self.fps))
        print("request frame num:", frame_num)
        while self.frame_counter < frame_num and not self.frame is None:
            try:
                self.frame = self.reader._readFrame()
                self.frame = self.frame[:,:,::-1]
                self.frame_counter += 1
                if not len(self.frame):
                    self.frame = None
            except:
                self.frame = None
        return self.frame
        
    def get_frame_interp(self, time):
        # return an interpolated frame at 'time'.  Because the video
        # streams are sequential, never ask for a time earlier than
        # the previous request!
        frame_num = int(round(time * self.fps))
        print("request frame num:", frame_num)
        while self.frame_counter < frame_num and not self.frame is None:
            try:
                self.frame = self.reader._readFrame()
                self.frame = self.frame[:,:,::-1]
                self.frame_counter += 1
                if not len(self.frame):
                    self.frame = None
            except:
                self.frame = None
        return self.frame
        
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

#
# work on generating video early for testing purposes
#
# fixme: deal with different input fps
# fixme: deal with beat sync (maybe?)
# fixme: better size & arrangement scheme
# fixme: borders around frames?
def render_combined_video(project, video_names, offsets):
    # 1080p
    output_w = 1920
    output_h = 1080
    output_fps = 30
    
    # open all video clips and advance to clap sync point
    videos = []
    for i, file in enumerate(video_names):
        v = VideoTrack()
        path = os.path.join(project, file)
        if v.open(path):
            #v.skip_secs(offsets[i] / 1000)
            videos.append(v)

    if len(videos) == 0:
        return

    cols = int(math.sqrt(len(videos)))
    rows = int(math.sqrt(len(videos)))
    if cols * rows < len(videos):
        cols += 1
    if cols * rows < len(videos):
        rows += 1
    print("video grid:", cols, "x", rows)
    cell_w = int(output_w / cols)
    cell_h = int(output_h / rows)
    cell_aspect = cell_w / cell_h
    print("  cell size:", cell_w, "x", cell_h, "aspect:", cell_aspect)
    
    # open writer for output
    inputdict = {
        '-r': str(output_fps)
    }
    lossless = {
        # See all options: https://trac.ffmpeg.org/wiki/Encode/H.264
        '-vcodec': 'libx264',  # use the h.264 codec
        '-crf': '0',           # set the constant rate factor to 0, (lossless)
        '-preset': 'veryslow', # maximum compression
        '-r': str(output_fps)  # match input fps
    }
    sane = {
        # See all options: https://trac.ffmpeg.org/wiki/Encode/H.264
        '-vcodec': 'libx264',  # use the h.264 codec
        '-crf': '17',          # visually lossless (or nearly so)
        '-preset': 'medium',   # default compression
        '-r': str(output_fps)  # match input fps
    }
    output_file = os.path.join(project, "group.mp4")
    writer = skvideo.io.FFmpegWriter(output_file, inputdict=inputdict, outputdict=sane)
    done = False
    frames = [None] * len(videos)
    output_time = 0
    while not done:
        done = True
        for i, v in enumerate(videos):
            offset_sec = offsets[i] / 1000
            frame = v.get_frame(output_time + offset_sec)
            if not frame is None:
                done = False
                (h, w) = frame.shape[:2]
                aspect = w/h
                scale_w = cell_w / w
                scale_h = cell_h / h
                if scale_w < scale_h:
                    print("scale width")
                    frame_scale = cv2.resize(frame, (0,0), fx=scale_w,
                                             fy=scale_w,
                                             interpolation=cv2.INTER_AREA)
                else:
                    frame_scale = cv2.resize(frame, (0,0), fx=scale_h,
                                             fy=scale_h,
                                             interpolation=cv2.INTER_AREA)
                    
                frames[i] = frame_scale
                # cv2.imshow(video_names[i], frame_scale)
            else:
                # fade
                frames[i] = (frames[i] * 0.9).astype('uint8')
                if np.any(frames[i]):
                    done = False
        if not done:
            main_frame = np.zeros(shape=[output_h, output_w, 3], dtype=np.uint8)
            row = 0
            col = 0
            for i, f in enumerate(frames):
                if not f is None:
                    x = col * cell_w
                    y = row * cell_h
                    main_frame[y:y+f.shape[0],x:x+f.shape[1]] = f
                row += 1
                if row >= rows:
                    row = 0
                    col += 1
            cv2.imshow("main", main_frame)
            cv2.waitKey(1)
            writer.writeFrame(main_frame[:,:,::-1])  #write the frame as RGB not BGR
            output_time += 1 / output_fps
    writer.close()

def merge(project):
    # use ffmpeg to combine the video and audio tracks into the final movie
    from subprocess import call
    input_video = os.path.join(project, "group.mp4")
    input_audio = os.path.join(project, "group.wav")
    output_video = os.path.join(project, "final.mp4")
    result = call(["ffmpeg", "-i", input_video, "-i", input_audio, "-c:v", "copy", "-c:a", "aac", output_video])
    print("ffmpeg result code:", result)
