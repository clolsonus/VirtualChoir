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

from lib.video_track import VideoTrack

parser = argparse.ArgumentParser(description='attempt to rescue a video track')
parser.add_argument('video', help='video file')
args = parser.parse_args()

dirname = os.path.dirname(args.video)
basename = os.path.basename(args.video)
rootname, ext = os.path.splitext(basename)

tmp_video = os.path.join(dirname, "tmp_video.mp4")
tmp_audio = os.path.join(dirname, "tmp_audio.mp3")
output_file = os.path.join(dirname, rootname + "-rescued.mp4")
print("rescued video name:", output_file)

# load and save
basename, ext = os.path.splitext(args.video)
sample = AudioSegment.from_file(args.video, ext[1:])
sample.export(tmp_audio, format="mp3")

v = VideoTrack()
v.open(args.video)

def gen_dicts(fps, quality="sane"):
    inputdict = {
        '-r': str(fps)
    }
    if quality == "sane":
        outputdict = {
            # See all options: https://trac.ffmpeg.org/wiki/Encode/H.264
            '-vcodec': 'libx264',  # use the h.264 codec
            '-pix_fmt': 'yuv420p', # support 'dumb' players
            '-crf': '17',          # visually lossless (or nearly so)
            '-preset': 'medium',   # default compression
            '-r': str(fps)         # fps
        }
    elif quality == "lossless":
        outputdict = {
            # See all options: https://trac.ffmpeg.org/wiki/Encode/H.264
            '-vcodec': 'libx264',  # use the h.264 codec
            '-pix_fmt': 'yuv420p', # support 'dumb' players
            '-crf': '0',           # set the constant rate factor to 0, (lossless)
            '-preset': 'veryslow', # maximum compression
            '-r': str(fps)         # fps
        }
    return inputdict, outputdict

# open destination
inputdict, outputdict = gen_dicts(v.fps, "sane")
writer = skvideo.io.FFmpegWriter(tmp_video, inputdict=inputdict, outputdict=outputdict)


# compute the g, b, and r histograms for the image (a scaling
# parameter can be set to improve performance at a tiny loss of
# resolution)
def get_histogram_rgb(rgb, scale=0.25):
    scaled = cv2.resize(rgb, (0,0), fx=scale, fy=scale)
    g, b, r = cv2.split(scaled)
    
    g_hist = np.bincount(g.ravel(), minlength=256)
    b_hist = np.bincount(b.ravel(), minlength=256)
    r_hist = np.bincount(r.ravel(), minlength=256)
    bins = np.arange(256)
    return (g_hist.astype("float32"),
            b_hist.astype("float32"),
            r_hist.astype("float32"))

clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(4,4))

# walk through video by time
pbar = tqdm(total=v.duration, smoothing=0.05)
t = 0
dt = 1 / v.fps
count = 0
g_template = None
b_template = None
r_template = None
accum = None
while not v.frame is None:
    v.get_frame(t)
    frame = v.raw_frame.copy()
    # small bit of down scaling while maintaining original aspect ratio
    target_area = 1280*720
    area = frame.shape[0] * frame.shape[1]
    #print("area:", area, "target_area:", target_area)
    if area > target_area:
        scale = math.sqrt( target_area / area )
        frame = cv2.resize(frame, (0,0), fx=scale, fy=scale,
                           interpolation=cv2.INTER_AREA)
    cv2.imshow("frame", frame)

    if True:
        thresh = cv2.inRange(frame, (0, 0, 175), (255, 255, 255))
        #kernel = np.ones((3,3), np.uint8)
        #thresh = cv2.dilate(thresh, kernel, 1)
        thresh_inv = cv2.bitwise_not(thresh)
        front = cv2.bitwise_and(frame, frame, mask=thresh)
        back = cv2.bitwise_and(frame, frame, mask=thresh_inv)
        cv2.imshow("front", front)
        cv2.imshow("back", back)
        #frame = front
        
        # forcing the histogram of just the background channel
        factor = 0.01
        #hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        #hue, sat, val = cv2.split(hsv)
        
        if accum is None:
            #template_file = "/home/curt/Downloads/IMG_20201121_120903264.jpg"
            #ref =  cv2.imread(template_file, flags=cv2.IMREAD_ANYCOLOR|cv2.IMREAD_ANYDEPTH|cv2.IMREAD_IGNORE_ORIENTATION)
            accum = back.copy().astype('float')
        else:
            accum = (1-factor)*accum + factor*back.astype('float')
        ref = accum.astype('uint8')
    
        #print(frame, ref)
        back = match_histograms(back, ref, multichannel=True)
        #back = cv2.blur(back, (3,3))
        # remask after fiddling with histogram
        back = cv2.bitwise_and(back, back, mask=thresh_inv)
        cv2.imshow("fixed", back)

        # and combine
        frame = back + front
        cv2.imshow("combine", frame)
            
    if False:
        # try histogram mashing
        if g_template is None or b_template is None or r_template is None:
            template_file = "/home/curt/Downloads/IMG_20201121_120903264.jpg"
            rgb =  cv2.imread(template_file, flags=cv2.IMREAD_ANYCOLOR|cv2.IMREAD_ANYDEPTH|cv2.IMREAD_IGNORE_ORIENTATION) 
            g_template, b_template, r_template = get_histogram_rgb(frame, 1)
        g_hist, b_hist, r_hist = get_histogram_rgb(frame, 1)
        g, b, r = cv2.split(frame)
        # interpolate linearly to find the pixel values in the template image
        # that correspond most closely to the quantiles in the source image
        src_g_quantiles = np.cumsum(g_hist)
        src_b_quantiles = np.cumsum(b_hist)
        src_r_quantiles = np.cumsum(r_hist)
        src_g_quantiles /= src_g_quantiles[-1]
        src_b_quantiles /= src_b_quantiles[-1]
        src_r_quantiles /= src_r_quantiles[-1]
    
        interp_g_values = np.interp(src_g_quantiles, g_template, np.arange(256))
        interp_b_values = np.interp(src_b_quantiles, b_template, np.arange(256))
        interp_r_values = np.interp(src_r_quantiles, r_template, np.arange(256))

        g = interp_g_values[g].reshape(g.shape).astype('uint8')
        b = interp_b_values[b].reshape(b.shape).astype('uint8')
        r = interp_r_values[r].reshape(r.shape).astype('uint8')

        fraem = cv2.merge( (g, b, r) )
        cv2.imshow("mash", frame)

    if False:
        # try clahe on the val channel
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hue, sat, val = cv2.split(hsv)
        aeq = clahe.apply(val)
        hsv = cv2.merge((hue, sat, aeq))
        frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        cv2.imshow("eq", frame)
    
    writer.writeFrame(frame[:,:,::-1])
    pbar.update(dt)
    t += dt
    cv2.waitKey(1)
writer.close()
pbar.close()

print("video: merging aligned video and audio into final result:", output_file)
# use ffmpeg to combine the video and audio tracks into the final movie
result = call(["ffmpeg", "-i", tmp_video, "-i", tmp_audio, "-c:v", "copy", "-c:a", "aac", "-y", output_file])
print("ffmpeg result code:", result)

# clean up
os.unlink(tmp_audio)
os.unlink(tmp_video)
