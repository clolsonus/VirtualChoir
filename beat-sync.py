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
import pyrubberband as pyrb               # pip install pyrubberband
from scipy import signal                  # spectrogram

parser = argparse.ArgumentParser(description='virtual choir')
parser.add_argument('videos', metavar='videos', nargs='+',
                    help='input videos')
args = parser.parse_args()

# function from: https://stackoverflow.com/questions/51434897/how-to-change-audio-playback-speed-using-pydub
def change_audioseg_tempo(segment, scale):
    y = np.array(segment.get_array_of_samples())
    if segment.channels == 2:
        y = y.reshape((-1, 2))

    sr = segment.frame_rate
    y_fast = pyrb.time_stretch(y, sr, scale)

    channels = 2 if (y_fast.ndim == 2 and y_fast.shape[1] == 2) else 1
    y = np.int16(y_fast * 2 ** 15)

    new_seg = AudioSegment(y.tobytes(), frame_rate=sr, sample_width=2, channels=channels)
    return new_seg

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

# analyze audio streams (using librosa functions)
hop_length = 512
onset_list = []
time_list = []
beat_list = []
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
    
# find nearly matching beats between clips and group them
import copy
scratch_list = copy.deepcopy(beat_list)
groups = []
for i in range(len(scratch_list)-1):
    beats1 = scratch_list[i]
    for b1 in beats1:
        if b1 < 0: continue
        group = [ (i, b1) ]
        for j in range(i+1, len(scratch_list)):
            beats2 = scratch_list[j]
            for n, b2 in enumerate(beats2):
                if abs(b1 - b2) < 0.15:
                    print("  track %d vs %d: %.3f %.3f" % (i, j, b1, b2))
                    group.append( (j, b2) )
                    beats2[n] = -1
        if len(group) > 1:
            groups.append(group)
            
print("beat groupings:")
# compute average time for each beat group (add it and label it -1)
for group in groups:
    sum = 0
    count = 0
    for i, t in group:
        sum += t
        count += 1
    average = sum / count
    group.append( (-1, average) )
    print(group)

# make time remapping templates
temperals = []
map_list = []
for i in range(len(beat_list)):
    time_mapping = []
    for group in groups:
        for j, t in group[:-1]:
            if i == j:
                time_mapping.append( (t, group[-1][1]) )
    time_mapping = sorted(time_mapping, key=lambda fields: fields[0])
    map_list.append(time_mapping)
    print("time_mapping:", time_mapping)

# deep dive, try to remap the timing of the clips for alignment ... scary part!
for i, sample in enumerate(samples):
    new = AudioSegment.empty()
    sr = sample.frame_rate
    offset = (clap_offset[i] / 1000) # secs
    trimval = int(round(clap_offset[i] * sr / 1000))
    time_map = map_list[i]
    for j in range(len(time_map)-1):
        src_interval = time_map[j+1][0] - time_map[j][0]
        dst_interval = time_map[j+1][1] - time_map[j][1]
        scale = dst_interval / src_interval
        print("intervals:", src_interval, dst_interval, "scale:", scale)
        c1 = int(round( (time_map[j][0] + offset) * 1000 ))
        c2 = int(round( (time_map[j+1][0] + offset) * 1000 ))
        clip = sample[c1:c2]
        print(c1, c2, len(sample), len(clip))
        #new.extend( librosa.effects.time_stretch(np.array(clip).astype('float'), scale) )
        new += change_audioseg_tempo(clip, scale)
        print(len(new))
    #playback.play(new)
    temperals.append(new)
     
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

# visualize audio streams (using librosa functions)
if True:
    # plot original (unaligned) onset envelope peaks
    fig, ax = plt.subplots(nrows=len(onset_list), sharex=True, sharey=True)
    for i in range(len(onset_list)):
        ax[i].plot(time_list[i], onset_list[i])

    # compute and plot chroma representation of clips (I notice the
    # timescale has an odd scaling, but doesn't seem to be a factor of
    # 2, or maybe it is, so ???)
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

# do a quick mix of temperals
print("quick mix of temperals...")
mixed = None
for i, v in enumerate(args.videos):
    print(" ", v)
    sample = temperals[i]
    if mixed is None:
        mixed = sample
    else:
        mixed = mixed.overlay(sample)
print("playing quick sync combined audio...")
playback.play(mixed)

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
