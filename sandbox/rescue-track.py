#!/usr/bin/env python3

# for tracks that don't time align (presumably because the reference
# track bogged somehow during playback and performance)

# load a text file that lists a set of time deltas and where they
# should apply.  then read the audio and vidoe tracks and make the
# appropriate corrections.

import argparse
import csv
import os
from pydub import AudioSegment  # pip install pydub
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
nudge_file = os.path.join(dirname, rootname + ".txt")
print(args.video, nudge_file)

nudges = []
offset = 0
total = 0
if not os.path.exists(nudge_file):
    print("Nothing to do, no nudge file found:", nudge_file)
    quit()
    
print("Loading:", nudge_file)
accum = 0.0
with open(nudge_file, 'r') as fp:
    reader = csv.reader(fp, delimiter=' ', skipinitialspace=True)
    for row in reader:
        print(row)
        if len(row) != 2:
            print("bad nudges file syntax:", row)
            continue
        if row[0] == "offset":
            offset = float(row[1])
        elif row[0] == "total":
            total = float(row[1])
        else:
            nudges.append([ float(row[0]), float(row[1])] )
            accum += float(row[1])
scale = abs(accum / total)
print("nudge total:", total, "accum:", accum, "scale:", scale)
for i in range(len(nudges)):
    nudges[i][1] *= scale
            
if len(nudges) == 0:
    print("no nudges found in nudges file, quitting.")
    quit()

tmp_video = os.path.join(dirname, "tmp_video.mp4")
tmp_audio = os.path.join(dirname, "tmp_audio.mp3")
output_file = os.path.join(dirname, rootname + "-rescued.mp4")
print("rescued video name:", output_file)

# load and fix the audio file
basename, ext = os.path.splitext(args.video)
sample = AudioSegment.from_file(args.video, ext[1:])
ref = offset
for n in nudges:
    if n[1] < 0:
        # snip
        t = n[0] - ref
        print("sample time:", t, "nudge:", n[1])
        blend = -n[1]*1000
        clip1 = sample[:t*1000]
        clip2 = sample[t*1000:]
        sample = clip1.append(clip2, crossfade=blend)
        ref += n[1]
    else:
        # pad
        print("pad not yet implemented, barf...")
        quit()
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

# walk through video by time (with nudges)
pbar = tqdm(total=v.duration, smoothing=0.05)
t = 0
dt = 1 / v.fps
ref = offset
count = 0
nudge_time = 0
while not v.frame is None:
    if count < len(nudges):
        if ref >= nudges[count][0]:
            nudge_time -= nudges[count][1]
            ref += nudges[count][1]
            count +=1
    #print("t:", t, "ref:", ref, "nudge", nudge_time)
    v.get_frame(t+nudge_time)
    frame = v.raw_frame.copy()
    # small bit of down scaling while maintaining original aspect ratio
    target_area = 1280*720
    area = frame.shape[0] * frame.shape[1]
    #print("area:", area, "target_area:", target_area)
    if area > target_area:
        scale = math.sqrt( target_area / area )
        frame = cv2.resize(frame, (0,0), fx=scale, fy=scale,
                           interpolation=cv2.INTER_AREA)
    writer.writeFrame(frame[:,:,::-1])
    pbar.update(dt)
    t += dt
    ref += dt
writer.close()
pbar.close()

print("video: merging aligned video and audio into final result:", output_file)
# use ffmpeg to combine the video and audio tracks into the final movie
result = call(["ffmpeg", "-i", tmp_video, "-i", tmp_audio, "-c:v", "copy", "-c:a", "aac", "-y", output_file])
print("ffmpeg result code:", result)

# clean up
os.unlink(tmp_audio)
os.unlink(tmp_video)
