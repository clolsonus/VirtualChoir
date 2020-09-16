#!/usr/bin/env python3

# https://librosa.org/doc/latest/auto_examples/plot_music_sync.html#sphx-glr-auto-examples-plot-music-sync-py

import argparse
import librosa                  # pip install librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
import os
import pycorrelate as pyc                # pip install pycorrelate
from pydub import AudioSegment, playback  # pip install pydub
import sys

parser = argparse.ArgumentParser(description='virtual choir')
parser.add_argument('videos', metavar='videos', nargs='+',
                    help='input videos')
args = parser.parse_args()

for v in args.videos:
    basename, ext = os.path.splitext(v)
    wavefile = basename + ".wav"
    if not os.path.exists(wavefile):
        print(v, basename, ext)
        command = "ffmpeg -i %s -map 0:1 -acodec pcm_s16le -ac 2 %s" % (v, wavefile)
        os.system(command)

# return postion of sync clap in ms
def find_sync_clap(raw, rate):
    for i, s in enumerate(raw):
        if abs(s) > 10000:
            return (i * 1000) / rate

def correlate(raw1, raw2):
    ycorr = pyc.ucorrelate(np.array(raw1), np.array(raw2), 11000)
    #ycorr = np.correlate(raw1, raw2)
    print(ycorr)
    return ycorr

# load samples, convert to mono, and normalize
print("loading samples...")
samples = []
raws = []
for v in args.videos:
    print(" ", v)
    basename, ext = os.path.splitext(v)
    sample = AudioSegment.from_file(v, ext[1:])
    sample = sample.set_channels(1) # convert to mono
    sample = sample.normalize()
    samples.append(sample)
    raw = sample.get_array_of_samples()
    raws.append(raw)

    if False:
        hop_length = 512
        oenv = librosa.onset.onset_strength(y=np.array(raw).astype('float'), sr=sample.frame_rate,
                                            hop_length=hop_length)
        tempogram = librosa.feature.tempogram(onset_envelope=oenv,
                                              sr=sample.frame_rate,
                                              hop_length=hop_length)
        print(tempogram.shape, tempogram)
        plt.figure()
        times = librosa.times_like(oenv, sr=sample.frame_rate,
                                   hop_length=hop_length)
        print(np.mean(oenv), np.std(oenv))
        plt.plot(times, oenv)
        plt.show()

    if False:
        plt.figure()
        M=1024
        from scipy import signal
        dt = 1 / sample.frame_rate
        freqs, times, Sx = signal.spectrogram(np.array(raw), fs=dt,
                                              window='hanning',
                                              nperseg=M, noverlap=M - 100,
                                              detrend=False, scaling='spectrum')
        f, ax = plt.subplots()
        ax.pcolormesh(times, freqs, 10 * np.log10(Sx), cmap='viridis')
        ax.set_title("Accelerometer Spectogram")
        ax.set_ylabel('Frequency [Hz]')
        ax.set_xlabel('Time [s]');
        plt.show()

# find first clap event in each sample
print("locating sync clap...")
clap_offset = []
min_sync = None
for i, sample in enumerate(samples):
    v = args.videos[i]
    raw = raws[i]
    rate = sample.frame_rate
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
plt.figure(1)
for i, sample in enumerate(samples):
    v = args.videos[i]
    raw = sample.get_array_of_samples()
    rate = sample.frame_rate
    sync_ms = clap_offset[i]
    print(" ", args.videos[i], sync_ms)
    plt.title(basename)
    hackval = int(round(sync_ms * rate / 1000))
    plt.plot(np.abs(raw[hackval:]))
plt.show()

if True:
    # work with librosa to sync audio streams
    fig, ax = plt.subplots(nrows=len(raws), sharex=True, sharey=True)
    for i in range(len(raws)):
        hackval = int(round(clap_offset[i] * rate / 1000))
        librosa.display.waveplot(np.array(raws[i][hackval:]).astype('float'), sr=sample.frame_rate, ax=ax[i])
        ax[i].set(title=args.videos[i])
        ax[i].label_outer()
    plt.show()

    hop_length = 1024
    chromas = []
    fig, ax = plt.subplots(nrows=len(raws), sharey=True)
    for i in range(len(raws)):
        hackval = int(round(clap_offset[i] * rate / 1000))
        chroma = librosa.feature.chroma_cqt(y=np.array(raws[i][hackval:]).astype('float'),
                                            sr=sample.frame_rate,
                                            hop_length=hop_length)
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

if False:
    print("playing quick sync combined audio...")
    playback.play(mixed)

ref = None
plt.figure(1)
for i, sample in enumerate(samples):
    print(args.videos[i])
    sync_ms = clap_offset[i]
    sample = sample[sync_ms:]
    raw = sample.get_array_of_samples()
    rate = sample.frame_rate
    if ref is None:
        ref = raw
        cor = 0
    else:
        cor = correlate(ref, raw)
    print(cor)
    plt.title(basename)
    plt.plot(cor)
plt.show()

    
