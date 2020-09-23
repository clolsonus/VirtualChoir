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

import analyze
import mixer
import video

parser = argparse.ArgumentParser(description='virtual choir')
parser.add_argument('project', help='project folder')
#parser.add_argument('videos', metavar='videos', nargs='+', help='input videos')
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

# find all the project clips (needs work?)
audio_extensions = [ "aiff", "m4a", "mp3", "wav" ]
video_extensions = [ "avi", "mov", "mp4" ]
audio_clips = []
video_clips = []
for file in os.listdir(args.project):
    basename, ext = os.path.splitext(file)
    if file == "group.wav":
        pass
    elif ext[1:].lower() in audio_extensions:
        audio_clips.append(file)
    elif ext[1:].lower() in video_extensions:
        video_clips.append(file)
    else:
        print("Unknown extenstion (skipping):", file)
if not len(audio_clips):
    audio_clips = video_clips
print("audio clips:", audio_clips)
print("video clips:", video_clips)

# load samples, normalize, then generate a mono version for analysis
print("loading samples...")
samples = []
raws = []
for clip in audio_clips:
    basename, ext = os.path.splitext(clip)
    path = os.path.join(args.project, clip)
    sample = AudioSegment.from_file(path, ext[1:])
    print(" ", clip, "rate:", sample.frame_rate, "channels:", sample.channels)
    sample = sample.set_frame_rate(48000)
    sample = sample.normalize()
    #sample = sample.apply_gain(-sample.max_dBFS)
    #sample = sample - 12
    samples.append(sample)
    mono = sample.set_channels(1) # convert to mono
    raw = mono.get_array_of_samples()
    raws.append(raw)

# analyze audio streams (using librosa functions) and save/load
# results from previous run
analyze.compute(args.project, audio_clips, samples, raws)
analyze.gen_plots(samples, raws, audio_clips, sync_offsets=None)

sync_offsets = []
if args.beat_sync:
    # assume first detected beat is the clap sync
    for i in range(len(analyze.beat_list)):
        sync_offsets.append( analyze.beat_list[i][0] * 1000) # ms units
    
    # shift all beat times for each clip so that the sync clap is at t=0.0
    for seq in analyze.beat_list:
        offset = seq[0]
        for i in range(len(seq)):
            seq[i] -= offset
        print(seq)

    # find nearly matching beats between clips and group them
    import copy
    scratch_list = copy.deepcopy(analyze.beat_list)
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
    temporals = []
    map_list = []
    for i in range(len(analyze.beat_list)):
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
        offset = (sync_offsets[i] / 1000) # secs
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
        temporals.append(new)
     
    # mix the temporals
    print("Mixing samples...")
    mixed = mixer.combine(audio_clips, temporals, sync_offsets=None,
                          pan_range=0.5, sync_jitter_ms=0)
else:
    # use beat correlation to align clips
    print("correlating samples")
    analyze.correlate()
    for i in range(len(analyze.offset_list)):
        sync_offsets.append( -analyze.offset_list[i] * 1000) # ms units
        
    print("Mixing samples...")
    mixed = mixer.combine(audio_clips, samples, sync_offsets,
                          pan_range=0.5, sync_jitter_ms=20)
    
print("playing synced audio...")
group_file = os.path.join(args.project, "group.wav")
mixed.export(group_file, format="wav", tags={'artist': 'Various artists', 'album': 'Best of 2011', 'comments': 'This album is awesome!'})
playback.play(mixed)

# render the new combined video
video.render_combined_video( video_clips, sync_offsets )

# use ffmpeg to combine the video and audio tracks into the final movie
from subprocess import call
result = call(["ffmpeg", "-i", "group.mp4", "-i", "group.wav", "-c:v", "copy", "-c:a", "aac", "final.mp4"])
print("ffmpeg result code:", result)

# plot basic clip waveforms
fig, ax = plt.subplots(nrows=len(raws), sharex=True, sharey=True)
for i in range(len(raws)):
    sr = samples[i].frame_rate
    trimval = int(round(sync_offset[i] * sr / 1000))
    librosa.display.waveplot(np.array(raws[i][trimval:]).astype('float'), sr=samples[i].frame_rate, ax=ax[i])
    ax[i].set(title=clips[i])
    ax[i].label_outer()
    for b in analyze.beat_list[i]:
        ax[i].axvline(x=b, color='b')
plt.show()

# visualize audio streams (using librosa functions)
analyze.gen_plots(samples, raws, sync_offset, clips)
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
        trimval = int(round(sync_offset[i] * sr / 1000))
        chroma = librosa.feature.chroma_cqt(y=np.array(raws[i][trimval:]).astype('float'),
                                            sr=sr, hop_length=hop_length)
        chromas.append(chroma)
        img = librosa.display.specshow(chroma, x_axis='time',
                                       y_axis='chroma',
                                       hop_length=hop_length, ax=ax[i])
        ax[i].set(title='Chroma Representation of ' + clips[i])
    fig.colorbar(img, ax=ax)

    plt.show()

    
