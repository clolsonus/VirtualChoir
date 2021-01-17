#!/usr/bin/env python3

# for tracks that don't time align (presumably because the reference
# track bogged somehow during playback and performance)

# load a text file that lists a set of time deltas and where they
# should apply.  then read the audio and vidoe tracks and make the
# appropriate corrections.

import argparse
import csv
import cv2
import math
import numpy as np
import os
from pydub import AudioSegment  # pip install pydub
from skimage import exposure
from skimage.exposure import match_histograms
import skvideo.io               # pip install sk-video
from subprocess import call
from tqdm import tqdm

from lib.video_face_dlib import FaceDetect
from lib.video_track import VideoTrack

parser = argparse.ArgumentParser(description='attempt to rescue a video track')
parser.add_argument('video', help='video file')
args = parser.parse_args()

dirname = os.path.dirname(args.video)
basename = os.path.basename(args.video)
rootname, ext = os.path.splitext(basename)

#tmp_video = os.path.join(dirname, "tmp_video.mp4")
#tmp_audio = os.path.join(dirname, "tmp_audio.mp3")
#output_file = os.path.join(dirname, rootname + "-rescued.mp4")
#print("rescued video name:", output_file)

# load and save
basename, ext = os.path.splitext(args.video)
sample = AudioSegment.from_file(args.video, ext[1:])
#sample.export(tmp_audio, format="mp3")

clahe = cv2.createCLAHE(clipLimit=3, tileGridSize=(8,8))

v = VideoTrack()
v.open(args.video)

face = FaceDetect()
face.interval = int(round(v.fps * 1))

# walk through video by time
pbar = tqdm(total=v.duration, smoothing=0.05)
t = 0
dt = 1 / v.fps
while not v.frame is None:
    v.get_frame(t)
    #frame = v.raw_frame.copy()

    if True:
        # try clahe on the val channel
        hsv = cv2.cvtColor(v.raw_frame, cv2.COLOR_BGR2HSV)
        hue, sat, val = cv2.split(hsv)
        aeq = clahe.apply(val)
        hsv = cv2.merge((hue, sat, aeq))
        frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        cv2.imshow("equalized", frame)

    # small bit of down scaling while maintaining original aspect ratio
    #target_area = 1280*720
    #area = frame.shape[0] * frame.shape[1]
    #print("area:", area, "target_area:", target_area)
    #if area > target_area:
    #    scale = math.sqrt( target_area / area )
    #    frame = cv2.resize(frame, (0,0), fx=scale, fy=scale,
    #                       interpolation=cv2.INTER_AREA)
    frame = face.find_face(v.raw_frame, t)
    if not frame is None:
        cv2.imshow("frame", frame)
    
    #writer.writeFrame(frame[:,:,::-1])
    pbar.update(dt)
    t += dt
    cv2.waitKey(1)
#writer.close()
pbar.close()

#print("video: merging aligned video and audio into final result:", output_file)
# use ffmpeg to combine the video and audio tracks into the final movie
#result = call(["ffmpeg", "-i", tmp_video, "-i", tmp_audio, "-c:v", "copy", "-c:a", "aac", "-y", output_file])
#print("ffmpeg result code:", result)

# clean up
#os.unlink(tmp_audio)
#os.unlink(tmp_video)
