# analyze audio streams (using librosa functions)

import json
import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
import os
from tqdm import tqdm

hop_length = 512

class SampleGroup():
    def __init__(self):
        self.onset_list = []
        self.time_list = []
        self.beat_list = []
        self.offset_list = []
        self.intensity_list = []
        self.clarity_list = []
    
    def load(self, filename, names):
        if not os.path.exists(filename):
            return False
        else:
            self.beat_list.clear()
            with open(filename, "r") as fp:
                clips = json.load(fp)
            for i, name in enumerate(names):
                print("loading:", name)
                self.beat_list.append( clips[name]["beats"] )
            return True

    def save(self, filename, names):
        # create dictionary of beat maps (by clip name)
        clips = {}
        for i, name in enumerate(names):
            clips[name] = {}
            clips[name]["beats"] = []
            for b in self.beat_list[i]:
                # trim to 3 decimal places
                clips[name]["beats"].append( int(round(b * 10000)) / 10000 )
        print("clips:", clips)

        with open(filename, "w") as fp:
            json.dump(clips, fp, indent=4)

    # def intensity(self, raw):
    #     intense = []
    #     base = 0
    #     while base < len(raw):
    #         intense.append(np.max(raw[base:base+hop_length]))
    #         base += hop_length
    #     return np.array(intense).astype('float')
    
    def compute_intensities(self, raws):
        print("Computing intensities...")
        self.intensity_list = []
        for raw in tqdm(raws):
            intensity = []
            base = 0
            while base < len(raw):
                intensity.append(np.max(raw[base:base+hop_length]))
                base += hop_length
            self.intensity_list.append( np.array(intensity).astype('float') )

    def compute_clarities(self, samples, raws):
        print("Computing clarities...")
        self.clarity_list = []
        self.chroma_list = []
        for i, raw in enumerate(tqdm(raws)):
            sr = samples[i].frame_rate
            chroma = librosa.feature.chroma_cqt(y=np.array(raw).astype('float'),
                                                sr=sr, hop_length=hop_length)
            self.chroma_list.append(chroma)
            a = len(self.time_list[i])
            b = len(self.intensity_list[i])
            c = chroma.shape[1]
            min = np.min([a, b, c])
            clarity = np.zeros(min)
            for j in range(min):
                clarity[j] = (chroma[:,j] < 0.2).sum() * self.intensity_list[i][j]
            self.clarity_list.append(clarity.T)

    def compute_basic(self, samples, raws):
        print("Computing onset envelope and times...")
        self.onset_list = []
        self.time_list = []
        for i, raw in enumerate(tqdm(raws)):
            # compute onset envelopes
            sr = samples[i].frame_rate
            oenv = librosa.onset.onset_strength(y=np.array(raw).astype('float'),
                                                sr=sr, hop_length=hop_length)
            t = librosa.times_like(oenv, sr=sr, hop_length=hop_length)
            self.onset_list.append(oenv)
            self.time_list.append(t)
            
    def compute_old(self, project, names, samples, raws):
        #beats_file = os.path.join(project, "beats.json")
        print("Computing onset envelope and beats...")
        for i, raw in enumerate(raws):
            # compute onset envelopes
            sr = samples[i].frame_rate
            oenv = librosa.onset.onset_strength(y=np.array(raw).astype('float'),
                                                sr=sr, hop_length=hop_length)
            t = librosa.times_like(oenv, sr=sr, hop_length=hop_length)
            self.onset_list.append(oenv)
            self.time_list.append(t)

            self.intensity_list.append( self.intensity(raw) )
            
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
                if oenv[i] > 5*std:
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
            self.beat_list.append(beats)

        if False:
            # compute intervals between beats (not used for anything right now)
            intervals = []
            for i in range(1, len(beats)):
                intervals.append( beats[i] - beats[i-1] )
            #print("intervals:", intervals)
            #print("median beat:", np.median(intervals))

    def correlate_by_beats(self, onset_ref, time_ref,
                           offset_shift=None, plot=False):
        # compute relative time offsets by best correlation
        for i in range(0, len(self.onset_list)):
            print(onset_ref.shape, self.onset_list[i].shape)
            ycorr = np.correlate(onset_ref, self.onset_list[i], mode='full')
            max_index = np.argmax(ycorr)
            print("max index:", max_index)
            if max_index > len(self.onset_list[i]):
                shift = max_index - len(self.onset_list[i])
                shift_time = time_ref[shift]
                plot1 = onset_ref
                plot2 = np.concatenate([np.zeros(shift), self.onset_list[i]])
                print(i, time_ref[shift])
            elif max_index < len(self.onset_list[i]):
                shift = len(self.onset_list[i]) - max_index
                shift_time = -self.time_list[i][shift]
                plot1 = np.concatenate([np.zeros(shift), onset_ref], axis=None)
                plot2 = self.onset_list[i]
                print(i, -self.time_list[i][shift])
            else:
                plot1 = onset_ref
                plot2 = self.onset_list[i]
                shift = 0
                shift_time = 0
                print(i, 0)
            self.offset_list.append(shift_time)
            if plot:
                plt.figure()
                plt.plot(ycorr)
                plt.figure()
                plt.plot(plot1, label=0)
                plt.plot(plot2, label=i)
                plt.legend()
                plt.show()
        if offset_shift is None:
            self.shift = np.max(self.offset_list)
        else:
            self.shift = offset_shift
        self.max_index = np.argmax(self.offset_list)
        for i in range(len(self.offset_list)):
            self.offset_list[i] -= self.shift

    def correlate_by_generic(self, metric_list, offset_shift=None, plot=False):
        # compute relative time offsets by best correlation
        num = len(metric_list)
        offset_matrix = np.zeros( (num, num) )
        for i in range(0, num):
            for j in range(i, num):
                print(i, j, metric_list[i].shape, metric_list[j].shape)
                ycorr = np.correlate(metric_list[i],
                                     metric_list[j],
                                     mode='full')
                max_index = np.argmax(ycorr)
                print("max index:", max_index)
                if max_index > len(metric_list[j]):
                    shift = max_index - len(metric_list[j])
                    shift_time = self.time_list[i][shift]
                    plot1 = metric_list[i]
                    plot2 = np.concatenate([np.zeros(shift),
                                            metric_list[j]])
                    print(i, j, self.time_list[i][shift])
                elif max_index < len(metric_list[j]):
                    shift = len(metric_list[j]) - max_index
                    shift_time = -self.time_list[j][shift]
                    plot1 = np.concatenate([np.zeros(shift),
                                            metric_list[i]], axis=None)
                    plot2 = metric_list[j]
                    print(i, -self.time_list[j][shift])
                else:
                    plot1 = metric_list[i]
                    plot2 = metric_list[j]
                    shift = 0
                    shift_time = 0
                    print(i, 0)
                offset_matrix[i, j] = shift_time
                offset_matrix[j, i] = -shift_time
                if plot:
                    plt.figure()
                    plt.plot(ycorr)
                    plt.figure()
                    plt.plot(plot1, label=i)
                    plt.plot(plot2, label=j)
                    plt.legend()
                    plt.show()
        print("offset_matrix:\n", offset_matrix)
        self.offset_list = []
        for i in range(num):
            diff_array = offset_matrix[0,:] - offset_matrix[i,:]
            median = np.median(diff_array)
            print(offset_matrix[i,:])
            print(diff_array)
            print(median, np.mean(diff_array), np.std(diff_array))
            self.offset_list.append(median)
        print(self.offset_list)
        if offset_shift is None:
            self.shift = np.max(self.offset_list)
        else:
            self.shift = offset_shift
        self.max_index = np.argmax(self.offset_list)
        for i in range(len(self.offset_list)):
            self.offset_list[i] -= self.shift

    # visualize audio streams (using librosa functions)
    def gen_plots(self, samples, raws, names, sync_offsets=None):
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
            if ( len(self.beat_list) ):
                for b in self.beat_list[i]:
                    ax[i].axvline(x=b, color='b')

        print("Onset envelope plot...")
        # plot original (unaligned) onset envelope peaks
        fig, ax = plt.subplots(nrows=len(self.onset_list),
                               sharex=True, sharey=True)
        for i in range(len(self.onset_list)):
            ax[i].plot(self.time_list[i], self.onset_list[i])

        print("Intensity plot...")
        fig, ax = plt.subplots(nrows=len(raws),
                               sharex=True, sharey=True)
        for i in range(len(raws)):
            #ax[i].plot(self.time_list[i], self.onset_list[i])
            a = len(self.time_list[i])
            b = len(self.intensity_list[i])
            min = np.min([a, b])
            print(i, len(self.time_list[i]), len(self.intensity_list[i]))
            ax[i].plot(self.time_list[i][:min], self.intensity_list[i][:min])
        
        # skip chroma plots for now on long samples, takes forever ...
        if True:
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
                img = librosa.display.specshow(self.chroma_list[i],
                                               x_axis='time',
                                               y_axis='chroma',
                                               hop_length=int(hop_length*0.5), ax=ax[i])
                ax[i].set(title='Chroma Representation of ' + names[i])
            fig.colorbar(img, ax=ax)

            print("Note clarity plot...")
            fig, ax = plt.subplots(nrows=len(raws),
                                   sharex=True, sharey=True)
            for i in range(len(raws)):
                a = len(self.time_list[i])
                c = self.clarity_list[i].shape[0]
                min = np.min([a, b, c])
                print(i, len(self.time_list[i]), len(self.intensity_list[i]),
                      self.chroma_list[i].shape[1])
                ax[i].plot(self.time_list[i][:min], self.clarity_list[i][:min])
        
        plt.show()
