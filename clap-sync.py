#!/usr/bin/env python3

# https://librosa.org/doc/latest/auto_examples/plot_music_sync.html#sphx-glr-auto-examples-plot-music-sync-py

# pyrubberband may offer a higher quality stretch/compress function

import argparse
import librosa                  # pip install librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
import os
import pycorrelate as pyc                # pip install pycorrelate
from pydub import AudioSegment, playback  # pip install pydub
from scipy import signal
import sys

parser = argparse.ArgumentParser(description='virtual choir')
parser.add_argument('videos', metavar='videos', nargs='+',
                    help='input videos')
args = parser.parse_args()

# return postion of sync clap in ms
def find_sync_clap(raw, rate):
    for i, s in enumerate(raw):
        if abs(s) > 10000:
            return (i * 1000) / rate

# load samples, convert to mono, and normalize
print("loading samples...")
samples = []
raws = []
for v in args.videos:
    print(" ", v)
    basename, ext = os.path.splitext(v)
    sample = AudioSegment.from_file(v, ext[1:])
    sample = sample.normalize()
    samples.append(sample)
    mono = sample.set_channels(1) # convert to mono
    raw = mono.get_array_of_samples()
    raws.append(raw)

# find first clap event in each sample
print("locating sync clap...")
clap_offset = []
min_sync = None
for i, raw in enumerate(raws):
    v = args.videos[i]
    raw = raws[i]
    rate = samples[i].frame_rate
    sync_ms = int(round(find_sync_clap(raw, rate)))
    print(" ", args.videos[i], sync_ms)
    clap_offset.append(sync_ms)
    if min_sync == None:
        min_sync = sync_ms
    elif sync_ms < min_sync:
        min_sync = sync_ms

# minimal trimming
for i in range(len(clap_offset)):
    clap_offset[i] -= min_sync

# plot synced signals
print("plot synced signals...")
fig, ax = plt.subplots(nrows=len(raws), sharex=True, sharey=True)
for i, raw in enumerate(raws):
    v = args.videos[i]
    rate = samples[i].frame_rate
    sync_ms = clap_offset[i]
    trimval = int(round(sync_ms * rate / 1000))
    print(" ", args.videos[i], sync_ms)
    ax[i].plot(np.array(raw[trimval:]))
plt.show()

# do a quick mix from starting clap
print("quick mix based on clap sync...")
mixed = None
for i, v in enumerate(args.videos):
    print(" ", v)
    sample = samples[i]
    sync_ms = clap_offset[i]
    if mixed is None:
        mixed = sample[sync_ms:]
    else:
        mixed = mixed.overlay(sample[sync_ms:])

if True:
    print("playing quick sync combined audio...")
    playback.play(mixed)
