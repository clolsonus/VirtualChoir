# analyze audio streams (using librosa functions)

import json
import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
import os

onset_list = []
time_list = []
beat_list = []
offset_list = []

hop_length = 512

def load(filename, names):
    if not os.path.exists(filename):
        return False
    else:
        beat_list.clear()
        with open(filename, "r") as fp:
            clips = json.load(fp)
        for i, name in enumerate(names):
            print("loading:", name)
            beat_list.append( clips[name]["beats"] )
        return True
    
def save(filename, names):
    # create dictionary of beat maps (by clip name)
    clips = {}
    for i, name in enumerate(names):
        clips[name] = {}
        clips[name]["beats"] = []
        for b in beat_list[i]:
            # trim to 3 decimal places
            clips[name]["beats"].append( int(round(b * 10000)) / 10000 )
    print("clips:", clips)

    with open(filename, "w") as fp:
        json.dump(clips, fp, indent=4)

def compute(project, names, samples, raws):
    #beats_file = os.path.join(project, "beats.json")
    print("Computing onset envelope and beats...")
    for i, raw in enumerate(raws):
        # compute onset envelopes
        sr = samples[i].frame_rate
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
        print(" ", names[i], mean, std, maximum)
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
                    #print("Beat: %.3f (%.1f)" % (beat_time, beat_max))
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

    if False:
        # compute intervals between beats (not used for anything right now)
        intervals = []
        for i in range(1, len(beats)):
            intervals.append( beats[i] - beats[i-1] )
        #print("intervals:", intervals)
        #print("median beat:", np.median(intervals))

    # compute relative time offsets by best correlation
    offset_list.append(0)
    for i in range(1, len(onset_list)):
        print(onset_list[0].shape, onset_list[i].shape)
        ycorr = np.correlate(onset_list[0], onset_list[i], mode='full')
        max_index = np.argmax(ycorr)
        print("max index:", max_index)
        if max_index > len(onset_list[i]):
            shift = max_index - len(onset_list[i])
            shift_time = time_list[0][shift]
            plot1 = onset_list[0]
            plot2 = np.concatenate([np.zeros(shift), onset_list[i]])
            print(i, time_list[0][shift])
        elif max_index < len(onset_list[i]):
            shift = len(onset_list[i]) - max_index
            shift_time = -time_list[i][shift]
            plot1 = np.concatenate([np.zeros(shift), onset_list[0]], axis=None)
            plot2 = onset_list[i]
            print(i, -time_list[i][shift])
        else:
            plot1 = onset_list[0]
            plot2 = onset_list[i]
            shift = 0
            shift_time = 0
            print(i, 0)
        offset_list.append(shift_time)
        if False:
            plt.figure()
            plt.plot(ycorr)
            plt.figure()
            plt.plot(plot1, label=0)
            plt.plot(plot2, label=i)
            plt.legend()
            plt.show()
    max = np.max(offset_list)
    for i in range(len(offset_list)):
        offset_list[i] -= max

# visualize audio streams (using librosa functions)
def gen_plots(samples, raws, names, sync_offsets=None):
    print("Generating basic clip waveform...")
    # plot basic clip waveforms
    fig, ax = plt.subplots(nrows=len(raws), sharex=True, sharey=True)
    for i in range(len(raws)):
        sr = samples[i].frame_rate
        if sync_offsets is None:
            trimval = 0
        else:
            trimval = int(round(sync_offsets[i] * sr / 1000))
        librosa.display.waveplot(np.array(raws[i][trimval:]).astype('float'), sr=samples[i].frame_rate, ax=ax[i])
        ax[i].set(title=names[i])
        ax[i].label_outer()
        for b in beat_list[i]:
            ax[i].axvline(x=b, color='b')

    print("Onset envelope plot...")
    # plot original (unaligned) onset envelope peaks
    fig, ax = plt.subplots(nrows=len(onset_list),
                           sharex=True, sharey=True)
    for i in range(len(onset_list)):
        ax[i].plot(time_list[i], onset_list[i])

    # skip chroma plots for now on long samples, takes forever ...
    if False:
        # compute and plot chroma representation of clips (notice: work
        # around displaying specshow that seems to assume stereo samples,
        # but we are passing in mono here)
        print("Generating chroma plot...")
        chromas = []
        fig, ax = plt.subplots(nrows=len(raws), sharex=True, sharey=True)
        for i in range(len(raws)):
            print(" ", names[i])
            sr = samples[i].frame_rate
            if sync_offsets is None:
                trimval = 0
            else:
                trimval = int(round(sync_offsets[i] * sr / 1000))
            chroma = librosa.feature.chroma_cqt(y=np.array(raws[i][trimval:]).astype('float'),
                                                sr=sr, hop_length=hop_length)
            chromas.append(chroma)
            img = librosa.display.specshow(chroma, x_axis='time',
                                           y_axis='chroma',
                                           hop_length=int(hop_length*0.5), ax=ax[i])
            ax[i].set(title='Chroma Representation of ' + names[i])
        fig.colorbar(img, ax=ax)

    plt.show()

