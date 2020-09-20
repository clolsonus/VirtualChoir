# analyze audio streams (using librosa functions)

import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np

onset_list = []
time_list = []
beat_list = []

hop_length = 512

def analyze(samples, raws):
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

# visualize audio streams (using librosa functions)
def gen_plots(samples, raws, clap_offset, names):
    # plot original (unaligned) onset envelope peaks
    fig, ax = plt.subplots(nrows=len(onset_list),
                           sharex=True, sharey=True)
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
        ax[i].set(title='Chroma Representation of ' + names[i])
    fig.colorbar(img, ax=ax)

    plt.show()

