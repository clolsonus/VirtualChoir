#!/usr/bin/env python3

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

# simple plot synced signals
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

# work with librosa to visualize audio streams
if True:
    # plot beat peaks
    hop_length = 512
    fig, ax = plt.subplots(nrows=len(raws), sharex=True, sharey=True)
    for i, raw in enumerate(raws):
        sync_ms = clap_offset[i]
        rate = samples[i].frame_rate
        trimval = int(round(sync_ms * rate / 1000))
        oenv = librosa.onset.onset_strength(y=np.array(raw[trimval:]).astype('float'),
                                            sr=samples[i].frame_rate,
                                            hop_length=hop_length)
        tempogram = librosa.feature.tempogram(onset_envelope=oenv,
                                              sr=samples[i].frame_rate,
                                              hop_length=hop_length)
        #print(tempogram.shape, tempogram)
        times = librosa.times_like(oenv, sr=samples[i].frame_rate,
                                   hop_length=hop_length)
        ax[i].plot(times, oenv)
        
        # ok, try a thing
        beat = 0
        in_beat = False
        mean = np.mean(oenv)
        std = np.std(oenv)
        maximum = np.max(oenv) * 10
        print(mean, std, maximum)
        beat_max = 0
        beat_time = 0
        last_beat = None
        intervals = []
        for i in range(len(times)):
            if oenv[i] > 5*std:
                in_beat = True
            else:
                if in_beat:
                    # just finished a beat
                    print("Beat: %.3f (%.1f)" % (beat_time, beat_max))
                    if last_beat:
                        interval = beat_time - last_beat
                        last_beat = beat_time
                        intervals.append(interval)
                    else:
                        last_beat = beat_time
                in_beat = False
                beat_max = 0
            if in_beat:
                if oenv[i] > beat_max:
                    beat_max = oenv[i]
                    beat_time = times[i]
        print(intervals)
        print("median beat:", np.median(intervals))


    if False:
        # plot raw spectrogram (this doesn't seem as useful as the chroma plot)
        fig, ax = plt.subplots(nrows=len(raws), sharex=True, sharey=True)
        for i, raw in enumerate(raws):
            M=1024
            dt = 1 / samples[i].frame_rate
            sync_ms = clap_offset[i]
            rate = samples[i].frame_rate
            trimval = int(round(sync_ms * rate / 1000))
            freqs, times, Sx = signal.spectrogram(np.array(raw[trimval:]), fs=dt,
                                                  window='hanning',
                                                  nperseg=M, noverlap=M - 100,
                                                  detrend=False, scaling='spectrum')
            ax[i].pcolormesh(times, freqs, 10 * np.log10(Sx), cmap='viridis')
            ax[i].set_title("Accelerometer Spectogram")
            ax[i].set_ylabel('Frequency [Hz]')
            ax[i].set_xlabel('Time [s]');

    fig, ax = plt.subplots(nrows=len(raws), sharex=True, sharey=True)
    for i in range(len(raws)):
        trimval = int(round(clap_offset[i] * rate / 1000))
        librosa.display.waveplot(np.array(raws[i][trimval:]).astype('float'), sr=samples[i].frame_rate, ax=ax[i])
        ax[i].set(title=args.videos[i])
        ax[i].label_outer()

    hop_length = 1024
    chromas = []
    fig, ax = plt.subplots(nrows=len(raws), sharex=True, sharey=True)
    for i in range(len(raws)):
        trimval = int(round(clap_offset[i] * rate / 1000))
        chroma = librosa.feature.chroma_cqt(y=np.array(raws[i][trimval:]).astype('float'),
                                            sr=samples[i].frame_rate,
                                            hop_length=hop_length)
        chromas.append(chroma)
        img = librosa.display.specshow(chroma, x_axis='time',
                                       y_axis='chroma',
                                       hop_length=hop_length, ax=ax[i])
        ax[i].set(title='Chroma Representation of ' + args.videos[i])
    fig.colorbar(img, ax=ax)

    if False:
        # this could possibly be used to find a series of sync offsets
        # between audio streams, but you need the same notes ...
        D, wp = librosa.sequence.dtw(X=chromas[0], Y=chromas[2], metric='cosine')
        wp_s = librosa.frames_to_time(wp, sr=samples[i].frame_rate, hop_length=hop_length)

        fig, ax = plt.subplots()
        img = librosa.display.specshow(D, x_axis='time', y_axis='time', sr=samples[i].frame_rate,
                                       cmap='gray_r', hop_length=hop_length, ax=ax)
        ax.plot(wp_s[:, 1], wp_s[:, 0], marker='o', color='r')
        ax.set(title='Warping Path on Acc. Cost Matrix $D$',
               xlabel='Time $(X_2)$', ylabel='Time $(X_1)$')
        fig.colorbar(img, ax=ax)

        from matplotlib.patches import ConnectionPatch

        fig, (ax1, ax2) = plt.subplots(nrows=2, sharex=True, sharey=True, figsize=(8, 4))

        # Plot x_2
        librosa.display.waveplot(np.array(raws[2][trimval:]).astype('float'), sr=samples[i].frame_rate, ax=ax2)
        ax2.set(title='track 2')

        # Plot x_1
        librosa.display.waveplot(np.array(raws[0][trimval:]).astype('float'), sr=samples[i].frame_rate, ax=ax1)
        ax1.set(title='track 0')
        ax1.label_outer()

        n_arrows = 20
        for tp1, tp2 in wp_s[::len(wp_s)//n_arrows]:
            # Create a connection patch between the aligned time points
            # in each subplot
            con = ConnectionPatch(xyA=(tp1, 0), xyB=(tp2, 0),
                                  axesA=ax1, axesB=ax2,
                                  coordsA='data', coordsB='data',
                                  color='r', linestyle='--',
                                  alpha=0.5)
            ax2.add_artist(con)

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
