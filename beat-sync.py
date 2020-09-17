#!/usr/bin/env python3

print("Note: this script is a work in progress and may not do anything useful yet!")
print("Experimentation and learning in progress ...")
print()

# https://librosa.org/doc/latest/auto_examples/plot_music_sync.html#sphx-glr-auto-examples-plot-music-sync-py

# pyrubberband may offer a higher quality stretch/compress function

import argparse
import librosa                  # pip install librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
import os
from pydub import AudioSegment, playback  # pip install pydub
from scipy import signal                  # spectrogram

parser = argparse.ArgumentParser(description='virtual choir')
parser.add_argument('videos', metavar='videos', nargs='+',
                    help='input videos')
args = parser.parse_args()

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

# use librosa to analyze audio streams
onset_list = []
time_list = []
beat_list = []
hop_length = 512
for i, raw in enumerate(raws):
    sr = samples[i].frame_rate
    #sync_ms = clap_offset[i]
    #trimval = int(round(sync_ms * rate / 1000))
    
    # compute onset envelopes
    oenv = librosa.onset.onset_strength(y=np.array(raw).astype('float'),
                                        sr=sr, hop_length=hop_length)
    t = librosa.times_like(oenv, sr=sr, hop_length=hop_length)
    onset_list.append(oenv)
    time_list.append(t)
    
    # make a list (times) of the dominant beats
    in_beat = False
    mean = np.mean(oenv)
    std = np.std(oenv)
    maximum = np.max(oenv) * 10
    print(mean, std, maximum)
    beat_max = 0
    beat_time = 0
    last_beat = None
    beats = []
    for i in range(0, len(t)):
        # skip/ignore beats in the first 1/2 second
        if t[i] < 0.5:
            continue
        if oenv[i] > 4*std:
            in_beat = True
        else:
            if in_beat:
                # just finished a beat
                print("Beat: %.3f (%.1f)" % (beat_time, beat_max))
                beats.append(beat_time)
                if last_beat:
                    interval = beat_time - last_beat
                    last_beat = beat_time
                else:
                    last_beat = beat_time
            in_beat = False
            beat_max = 0
        if in_beat:
            if oenv[i] > beat_max:
                beat_max = oenv[i]
                beat_time = t[i]
    beat_list.append(beats)
    
    intervals = []
    for i in range(1, len(beats)):
        intervals.append( beats[i] - beats[i-1] )
    print(intervals)
    print("median beat:", np.median(intervals))

# assume first detected beat is the clap sync
clap_offset = []
for i in range(len(beat_list)):
    clap_offset.append( beat_list[i][0] * 1000) # ms units

# shift all beat times for each clip so that the sync clap is at t=0.0
for beats in beat_list:
    offset = beats[0]
    for i in range(len(beats)):
        beats[i] -= offset
    print(beats)
    
# try to find nearly matching beats between clips
for i in range(len(beat_list)-1):
    beats1 = beat_list[i]
    for j in range(i+1, len(beat_list)):
        print(i, j)
        beats2 = beat_list[j]
        for b1 in beats1:
            for b2 in beats2:
                if abs(b1 - b2) < 0.15:
                    print("  track %d vs %d: %.3f %.3f" % (i, j, b1, b2))
        
# plot basic clip waveforms
fig, ax = plt.subplots(nrows=len(raws), sharex=True, sharey=True)
for i in range(len(raws)):
    sr = samples[i].frame_rate
    trimval = int(round(clap_offset[i] * sr / 1000))
    librosa.display.waveplot(np.array(raws[i][trimval:]).astype('float'), sr=samples[i].frame_rate, ax=ax[i])
    ax[i].set(title=args.videos[i])
    ax[i].label_outer()
    for b in beat_list[i]:
        ax[i].axvline(x=b, color='b')

# work with librosa to visualize audio streams
if True:
    # plot original (unaligned) onset envelope peaks
    fig, ax = plt.subplots(nrows=len(onset_list), sharex=True, sharey=True)
    for i in range(len(onset_list)):
        ax[i].plot(time_list[i], onset_list[i])

    # compute and plot chroma representation of clips (I notice the
    # timescale has an odd scaling, but doesn't seem to be a factor of
    # 2, or maybe it is, so ???)
    hop_length = 512
    chromas = []
    fig, ax = plt.subplots(nrows=len(raws), sharex=True, sharey=True)
    for i in range(len(raws)):
        sr = samples[i].frame_rate
        trimval = int(round(clap_offset[i] * sr / 1000))
        chroma = librosa.feature.chroma_cqt(y=np.array(raws[i][trimval:]).astype('float'),
                                            sr=sr, hop_length=hop_length)
        chromas.append(chroma)
        img = librosa.display.specshow(chroma, x_axis='time',
                                       y_axis='chroma',
                                       hop_length=hop_length, ax=ax[i])
        ax[i].set(title='Chroma Representation of ' + args.videos[i])
    fig.colorbar(img, ax=ax)

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
