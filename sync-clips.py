#!/usr/bin/env python3

import argparse
import librosa                  # pip install librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
import os
from pydub import AudioSegment, playback  # pip install pydub
import pyrubberband as pyrb               # pip install pyrubberband
from scipy import signal                  # spectrogram

import beats
import video

parser = argparse.ArgumentParser(description='virtual choir')
parser.add_argument('videos', metavar='videos', nargs='+', help='input videos')
parser.add_argument('--beat-sync', action='store_true', help='do additional beat syncronization work to tighten up slight note timing misses')
args = parser.parse_args()

# function copied from: https://stackoverflow.com/questions/51434897/how-to-change-audio-playback-speed-using-pydub
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

# load samples, normalize, then generate a mono version for analysis
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

# analyze audio streams (using librosa functions) and save/load
# results from previous run
if not beats.load("beats.json", args.videos):
    beats.analyze(samples, raws)
    beats.save("beats.json", args.videos)
beats.gen_plots(samples, raws, args.videos, clap_offset=None)

# assume first detected beat is the clap sync
clap_offset = []
for i in range(len(beats.beat_list)):
    clap_offset.append( beats.beat_list[i][0] * 1000) # ms units

# shift all beat times for each clip so that the sync clap is at t=0.0
for seq in beats.beat_list:
    offset = seq[0]
    for i in range(len(seq)):
        seq[i] -= offset
    print(seq)

# render the new combined video
video.render_combined_video( args.videos, clap_offset )

if args.beat_sync:
    # find nearly matching beats between clips and group them
    import copy
    scratch_list = copy.deepcopy(beats.beat_list)
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
    for i in range(len(beats.beat_list)):
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
        time_map = map_list[i]
        for j in range(len(time_map)-1):
            src_interval = time_map[j+1][0] - time_map[j][0]
            dst_interval = time_map[j+1][1] - time_map[j][1]
            print("intervals:", src_interval, dst_interval)
            if dst_interval < 0.2 or src_interval < 0.2:
                speed = 1.0
            else:
                speed = src_interval / dst_interval
            print("intervals:", src_interval, dst_interval, "speed:", speed)
            c1 = int(round( (time_map[j][0] + offset) * 1000 ))
            c2 = int(round( (time_map[j+1][0] + offset) * 1000 ))
            clip = sample[c1:c2]
            #new.extend( librosa.effects.time_stretch(np.array(clip).astype('float'), scale) )
            if abs(1.0 - speed) < 0.0001:
                print("straight copy")
                newclip = clip
            elif speed < 0.9 or speed > 1.1:
                print("intervals too different, just straight copying")
                newclip = clip
            else:
                # adjust clip length
                newclip = change_audioseg_tempo(clip, speed)
            new += newclip
            print(" ", c1, c2, len(sample), len(clip), len(newclip))
        # c2 inherits last clip end, so add from there on to complete the clip
        new += sample[c2:]
        #playback.play(new)
        temperals.append(new)
     
    # mix the temperals
    print("mixing the temperals...")
    mixed = None
    for i, v in enumerate(args.videos):
        print(" ", v)
        sample = temperals[i]
        if mixed is None:
            mixed = sample
        else:
            mixed = mixed.overlay(sample)
    print("playing beat synced audio...")
    mixed.export("group.wav", format="wav", tags={'artist': 'Various artists', 'album': 'Best of 2011', 'comments': 'This album is awesome!'})
    playback.play(mixed)
    
else:
    # no beat syncing, just align and mix audio clips based on starting clap
    print("straight mixing based on clap sync...")
    mixed = None
    for i, sample in enumerate(samples):
        print(" ", args.videos[i])
        sync_ms = clap_offset[i]
        if mixed is None:
            mixed = sample[sync_ms:]
        else:
            mixed = mixed.overlay(sample[sync_ms:])
    print("playing clap synced audio...")
    mixed.export("group.wav", format="wav", tags={'artist': 'Various artists', 'album': 'Best of 2011', 'comments': 'This album is awesome!'})
    print("before")
    # playback.play(mixed)
    print("after")

# use ffmpeg to combine the video and audio tracks into the final movie
from subprocess import call
result = call(["ffmpeg", "-i", "group.mp4", "-i", "group.wav", "-c:v", "copy", "-c:a", "aac", "final.mp4"])
print("ffmpeg result code:", result)

# plot basic clip waveforms
fig, ax = plt.subplots(nrows=len(raws), sharex=True, sharey=True)
for i in range(len(raws)):
    sr = samples[i].frame_rate
    trimval = int(round(clap_offset[i] * sr / 1000))
    librosa.display.waveplot(np.array(raws[i][trimval:]).astype('float'), sr=samples[i].frame_rate, ax=ax[i])
    ax[i].set(title=args.videos[i])
    ax[i].label_outer()
    for b in beats.beat_list[i]:
        ax[i].axvline(x=b, color='b')

# visualize audio streams (using librosa functions)
beats.gen_plots(samples, raws, clap_offset, args.videos)
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

    
