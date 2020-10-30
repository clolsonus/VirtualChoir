import cv2
import json
import math
import numpy as np
import os
import skvideo.io               # pip install sk-video
from subprocess import call
from tqdm import tqdm

from .logger import log

class VideoTrack:
    def __init__(self):
        self.reader = None

    def open(self, file):
        print("video:", file)
        metadata = skvideo.io.ffprobe(file)
        #print(metadata.keys())
        if not "video" in metadata:
            return False
        #print(json.dumps(metadata["video"], indent=4))
        fps_string = metadata['video']['@r_frame_rate']
        (num, den) = fps_string.split('/')
        self.fps = float(num) / float(den)
        codec = metadata['video']['@codec_long_name']
        self.w = int(metadata['video']['@width'])
        self.h = int(metadata['video']['@height'])
        self.duration = float(metadata['video']['@duration'])
        self.total_frames = int(round(self.duration * self.fps))
        self.frame_counter = -1
        self.frame = []

        print('fps:', self.fps)
        print('codec:', codec)
        print('output size:', self.w, 'x', self.h)
        print('total frames:', self.total_frames)

        print("Opening ", file)
        self.reader = skvideo.io.FFmpegReader(file, inputdict={}, outputdict={})
        self.get_frame(0.0)     # read first frame
        return True

    def get_frame(self, time):
        # return the frame closest to the requested time
        frame_num = int(round(time * self.fps))
        # print("request frame num:", frame_num)
        if frame_num < 0:
            if self.frame is None:
                return np.zeros(shape=[self.h, self.w, 3], dtype=np.uint8)
            else:
                (h, w) = self.frame.shape[:2]
                return np.zeros(shape=[h, w, 3],
                                dtype=np.uint8)
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
# fixme: need to consider portrait video aspect ratios
# fixme: figure out why zooming on some landscape videos in some cases
#        doesn't always fill the grid cell (see Coeur, individual grades.) 
def render_combined_video(project, results_dir,
                          video_names, offsets, rotate_hints={},
                          title_page=None, credits_page=None):
    # 1080p
    output_w = 1920
    output_h = 1080
    output_fps = 30
    border = 10
    log("output video specs:", output_w, "x", output_h, "fps:", output_fps)
    
    # load static pages if specified
    if title_page:
        log("adding a title page:", title_page)
        title_rgb = cv2.imread(os.path.join(project, title_page),
                               flags=cv2.IMREAD_ANYCOLOR|cv2.IMREAD_ANYDEPTH)
        title_frame = np.zeros(shape=[output_h, output_w, 3], dtype=np.uint8)
        (h, w) = title_rgb.shape[:2]
        scale_w = output_w / w
        scale_h = output_h / h
        if scale_w < scale_h:
            title_scale = cv2.resize(title_rgb, (0,0), fx=scale_w,
                                     fy=scale_w,
                                     interpolation=cv2.INTER_AREA)
        else:
            title_scale = cv2.resize(title_rgb, (0,0), fx=scale_h,
                                     fy=scale_h,
                                     interpolation=cv2.INTER_AREA)
        x = int((output_w - title_scale.shape[1]) / 2)
        y = int((output_h - title_scale.shape[0]) / 2)
        title_frame[y:y+title_scale.shape[0],x:x+title_scale.shape[1]] = title_scale
        #cv2.imshow("title", title_frame)
        
    credits_frame = np.zeros(shape=[output_h, output_w, 3], dtype=np.uint8)
    if credits_page:
        log("adding a credits page:", credits_page)
        credits_rgb = cv2.imread(os.path.join(project, credits_page),
                                 flags=cv2.IMREAD_ANYCOLOR|cv2.IMREAD_ANYDEPTH)
        (h, w) = credits_rgb.shape[:2]
        scale_w = output_w / w
        scale_h = output_h / h
        if scale_w < scale_h:
            credits_scale = cv2.resize(credits_rgb, (0,0), fx=scale_w,
                                     fy=scale_w,
                                     interpolation=cv2.INTER_AREA)
        else:
            credits_scale = cv2.resize(credits_rgb, (0,0), fx=scale_h,
                                     fy=scale_h,
                                     interpolation=cv2.INTER_AREA)
        x = int((output_w - credits_scale.shape[1]) / 2)
        y = int((output_h - credits_scale.shape[0]) / 2)
        credits_frame[y:y+credits_scale.shape[0],x:x+credits_scale.shape[1]] = credits_scale
        #cv2.imshow("credits", credits_frame)

    # open all video clips and advance to clap sync point
    videos = []
    durations = []
    for i, file in enumerate(video_names):
        v = VideoTrack()
        path = os.path.join(project, file)
        if v.open(path):
            videos.append(v)
            durations.append(v.duration + offsets[i])
    duration = np.median(durations)
    duration += 4 # for credits/fade out
    log("median video duration (with fade to credits):", duration)
    
    if len(videos) == 0:
        return

    # plan our grid
    num_portrait = 0
    num_landscape = 0
    for v in videos:
        if not v.frame is None:
            (h, w) = v.frame.shape[:2]
            if w > h:
                num_landscape += 1
            else:
                num_portrait += 1
    landscape = True
    if num_portrait > num_landscape:
        landscape = False
        log("portrait dominant input videos")
    else:
        log("landscape dominant input videos")

    cols = 1
    rows = 1
    while cols * rows < len(videos):
        if landscape:
            if cols <= rows:
                cols += 1
            else:
                rows += 1
        else:
            if cols < rows*4:
                cols += 1
            else:
                rows += 1
    log("video grid (rows x cols):", rows, "x", cols)
    grid_w = int(output_w / cols)
    grid_h = int(output_h / rows)
    cell_w = (output_w - border*(cols+1)) / cols
    cell_h = (output_h - border*(rows+1)) / rows
    cell_aspect = cell_w / cell_h
    print("  grid size:", grid_w, "x", grid_h)
    print("  cell size:", cell_w, "x", cell_h, "aspect:", cell_aspect)
    
    # open writer for output
    inputdict = {
        '-r': str(output_fps)
    }
    lossless = {
        # See all options: https://trac.ffmpeg.org/wiki/Encode/H.264
        '-vcodec': 'libx264',  # use the h.264 codec
        '-pix_fmt': 'yuv420p', # support 'dumb' players
        '-crf': '0',           # set the constant rate factor to 0, (lossless)
        '-preset': 'veryslow', # maximum compression
        '-r': str(output_fps)  # match input fps
    }
    sane = {
        # See all options: https://trac.ffmpeg.org/wiki/Encode/H.264
        '-vcodec': 'libx264',  # use the h.264 codec
        '-pix_fmt': 'yuv420p', # support 'dumb' players
        '-crf': '17',          # visually lossless (or nearly so)
        '-preset': 'medium',   # default compression
        '-r': str(output_fps)  # match input fps
    }
    output_file = os.path.join(results_dir, "silent_video.mp4")
    writer = skvideo.io.FFmpegWriter(output_file, inputdict=inputdict, outputdict=sane)
    done = False
    frames = [None] * len(videos)
    output_time = 0
    pbar = tqdm(total=int(duration*output_fps), smoothing=0.1)
    while output_time <= duration:
        for i, v in enumerate(videos):
            frame = v.get_frame(output_time - offsets[i])
            if not frame is None:
                basevid = os.path.basename(video_names[i])
                #print("basevid:", basevid)
                if basevid in rotate_hints:
                    if rotate_hints[basevid] == 90:
                        frame = cv2.transpose(frame)
                        frame = cv2.flip(frame, 1)
                    elif rotate_hints[basevid] == 180:
                        frame = cv2.flip(frame, -1)
                    elif rotate_hints[basevid] == 270:
                        frame = cv2.transpose(frame)
                        frame = cv2.flip(frame, 0)
                    else:
                        print("unhandled rotation angle:", rotate_hints[video_names[i]])
                (h, w) = frame.shape[:2]
                aspect = w/h
                scale_w = cell_w / w
                scale_h = cell_h / h
                #option = "fit"
                option = "zoom"
                if option == "fit":
                    if scale_w < scale_h:
                        frame_scale = cv2.resize(frame, (0,0), fx=scale_w,
                                                 fy=scale_w,
                                                 interpolation=cv2.INTER_AREA)
                    else:
                        frame_scale = cv2.resize(frame, (0,0), fx=scale_h,
                                                 fy=scale_h,
                                                 interpolation=cv2.INTER_AREA)
                    frames[i] = frame_scale
                elif option == "zoom":
                    if scale_w < scale_h:
                        frame_scale = cv2.resize(frame, (0,0), fx=scale_h,
                                                 fy=scale_h,
                                                 interpolation=cv2.INTER_AREA)
                        (tmp_h, tmp_w) = frame_scale.shape[:2]
                        cut = int((tmp_w - cell_w) * 0.5)
                        frame_scale = frame_scale[:,cut:cut+int(round(cell_w))]
                    else:
                        frame_scale = cv2.resize(frame, (0,0), fx=scale_w,
                                                 fy=scale_w,
                                                 interpolation=cv2.INTER_AREA)
                        (tmp_h, tmp_w) = frame_scale.shape[:2]
                        cut = int((tmp_h - cell_h) * 0.5)
                        frame_scale = frame_scale[cut:cut+int(round(cell_h)),:]
                    frames[i] = frame_scale
                # cv2.imshow(video_names[i], frame_scale)
            else:
                # fade
                frames[i] = (frames[i] * 0.9).astype('uint8')
        main_frame = np.zeros(shape=[output_h, output_w, 3], dtype=np.uint8)

        row = 0
        col = 0
        for i, f in enumerate(frames):
            if not f is None:
                x = int(round(border + col * (cell_w + border)))
                y = int(round(border + row * (cell_h + border)))
                main_frame[y:y+f.shape[0],x:x+f.shape[1]] = f
            col += 1
            if col >= cols:
                col = 0
                row += 1
        #cv2.imshow("main", main_frame)

        if title_page and output_time <= 5:
            if output_time < 4:
                alpha = 1
            elif output_time >= 4 and output_time <= 5:
                alpha = (5 - output_time) / (5 - 4)
            else:
                alpha = 0
            #print("time:", output_time, "alpha:", alpha)
            output_frame = cv2.addWeighted(title_frame, alpha, main_frame, 1 - alpha, 0)
        elif output_time >= duration - 5:
            if output_time >= duration - 4:
                alpha = 1
            elif output_time >= duration - 5 and output_time < duration - 4:
                alpha = 1 - ((duration - 4) - output_time) / (5 - 4)
            else:
                alpha = 0
            #print("time:", output_time, "alpha:", alpha)
            output_frame = cv2.addWeighted(credits_frame, alpha, main_frame, 1 - alpha, 0)
        else:
            output_frame = main_frame
        cv2.imshow("output", output_frame)
        cv2.waitKey(1)

        writer.writeFrame(output_frame[:,:,::-1])  #write the frame as RGB not BGR
        output_time += 1 / output_fps
        pbar.update(1)
    pbar.close()
    writer.close()
    log("gridded video (only) file: silent_video.mp4")
    
def merge(results_dir):
    log("video: merging video and audio into final result: gridded_video.mp4")
    # use ffmpeg to combine the video and audio tracks into the final movie
    input_video = os.path.join(results_dir, "silent_video.mp4")
    input_audio = os.path.join(results_dir, "mixed_audio.mp3")
    output_video = os.path.join(results_dir, "gridded_video.mp4")
    result = call(["ffmpeg", "-i", input_video, "-i", input_audio, "-c:v", "copy", "-c:a", "aac", "-y", output_video])
    print("ffmpeg result code:", result)

# https://superuser.com/questions/258032/is-it-possible-to-use-ffmpeg-to-trim-off-x-seconds-from-the-beginning-of-a-video/269960
# ffmpeg -i input.flv -ss 2 -vcodec copy -acodec copy output.flv
#   -vcodec libx264 -crf 0

#ffmpeg -f lavfi -i color=c=black:s=1920x1080:r=25:d=1 -i testa444.mov -filter_complex "[0:v] trim=start_frame=1:end_frame=5 [blackstart]; [0:v] trim=start_frame=1:end_frame=3 [blackend]; [blackstart] [1:v] [blackend] concat=n=3:v=1:a=0[out]" -map "[out]" -c:v qtrle -c:a copy -timecode 01:00:00:00 test16.mov

def trim_videos(project, video_names, offsets):
    for video in video_names:
        input_file = os.path.join(project, video)
        head, tail = os.path.split(input_file)
        output_file = os.path.join(head, "aligned" + tail)
        result = call(["ffmpeg", "-i", input_video, "-ss", offsets[i],
                       "-vcodec", "libx264", "-acodec", "copy", output_file])
