# analyze audio streams (using librosa functions)

import json
import librosa
import librosa.display
import math
import matplotlib.pyplot as plt
import numpy as np
import os
from pydub import AudioSegment, scipy_effects # pip install pydub
from subprocess import call
from tqdm import tqdm

from .logger import log
from . import scan

sample_rate = 48000
hop_length = 512

class SampleGroup():
    def __init__(self, path):
        self.path = path
        self.name_list = []
        self.video_list = []
        self.sample_list = []
        self.raw_list = []
        self.onset_list = []
        self.time_list = []
        self.beat_list = []
        self.offset_list = []
        self.intensity_list = []
        self.clarity_list = []
        self.rms_list = []
        self.note_list = []
        self.envelope_list = []
        self.suppress_list = None
        self.leadin_list = []
        self.fadeout_list = []
        self.aup_file = None

    def load_all_samples_deprecated(self):
        audio_tracks, video_tracks, aup_file = scan.scan_directory(self.path)
        log("loading audio tracks:", audio_tracks)
        self.name_list = audio_tracks
        self.aup_file = aup_file
        max_frame_rate = 0
        self.sample_list = []
        for track in self.name_list:
            #print("track:", track)
            basename, ext = os.path.splitext(track)
            #print(basename, ext)
            path = os.path.join(self.path, track)
            if ext == ".aif":
                ext = ".aiff"
            try:
                sample = AudioSegment.from_file(path, ext[1:])
            except:
                sample = AudioSegment.silent(duration=10000)
            sample = sample.set_channels(2) # force samples to be stereo
            sample = sample.set_sample_width(2) # force to 2 for this project
            sample = sample.normalize()
            if sample.frame_rate > max_frame_rate:
                max_frame_rate = sample.frame_rate
            log(" ", track, "rate:", sample.frame_rate,
                "channels:", sample.channels, "width:", sample.sample_width)
            self.sample_list.append(sample)
            
        log("resampling all tracks at max frame rate:", max_frame_rate)
        for i, sample in enumerate(self.sample_list):
            self.sample_list[i] = self.sample_list[i].set_frame_rate(max_frame_rate)

    def check_cache(self):
        # make cache directory (if it doesn't exist)
        cache_dir = os.path.join(self.path, "cache")
        if not os.path.exists(cache_dir):
            log("Creating:", cache_dir)
            os.makedirs(cache_dir)
        return cache_dir
        
    def scan(self):
        audio_tracks, video_tracks, aup_file = scan.scan_directory(self.path)
        log("found audio tracks:", audio_tracks)
        self.name_list = audio_tracks
        self.video_list = video_tracks
        self.aup_file = aup_file

    def load(self, file):
        log("loading audio track:", file)
        basename, ext = os.path.splitext(file)
        # print(self.path, basename, ext)
        path = os.path.join(self.path, file)

        if not os.path.exists(path):
            return None
        
        if ext == ".aif":
            ext = ".aiff"
        elif ext == ".mpeg" or ext == ".m4v":
            ext = ".mp4"
        try:
            sample = AudioSegment.from_file(path, ext[1:])
        except Exception as e:
            # create a song of silence if sample load fails
            log("NOTICE: loading audio failed for:", file)
            log(str(e))
            sample = AudioSegment.silent(duration=10000)
        sample = sample.set_channels(2) # force samples to be stereo
        sample = sample.set_sample_width(2) # force to 2 for this project
        sample = sample.normalize()
        sample = sample.set_frame_rate(sample_rate)
        return sample

    def load_samples(self):
        cache_dir = self.check_cache()
        
        log("Load original samples and convert to canonical form...")
        self.sample_list = []
        for i, file in enumerate(self.name_list):
            # check cache
            fullname = os.path.join(self.path, file)
            name = os.path.basename(file)
            basename, ext = os.path.splitext(name)
            canon_name = os.path.join(self.path, "cache",
                                      basename + "-canon.mp3")
            sample = self.load(file)
            self.sample_list.append(sample)
            if not self.is_newer(canon_name, fullname):
                # save canonical version of audio in cache
                sample.export(canon_name, format="mp3")
        
    def compute_raw(self):
        cache_dir = self.check_cache()
        
        log("Generating raw signals...")
        self.raw_list = []
        for i, file in enumerate(self.name_list):
            # check cache
            fullname = os.path.join(self.path, file)
            name = os.path.basename(file)
            basename, ext = os.path.splitext(name)
            canon_name = os.path.join(self.path, "cache",
                                      basename + "-canon.mp3")
            mono_name = os.path.join(self.path, "cache",
                                     basename + "-monofilt.npy")
            if self.is_newer(mono_name, canon_name):
                # print("loading from cache:", mono_name)
                with open(mono_name, "rb") as f:
                    raw = np.load(f)
            else:
                # compute
                log("Generating mono/filtered sample:", mono_name)
                sample = self.sample_list[i]
                mono = sample.set_channels(1) # convert to mono
                mono_filt = scipy_effects.band_pass_filter(mono, 130, 523) #C3-C5
                raw = mono_filt.get_array_of_samples()
                # save in cache
                with open(mono_name, "wb") as f:
                    np.save(f, raw)
            self.raw_list.append(raw)
            
    def compute_onset(self):
        print("Computing onset envelope and times...")
        self.onset_list = []
        self.time_list = []
        for i, raw in enumerate(tqdm(self.raw_list)):
            # compute onset envelopes
            oenv = librosa.onset.onset_strength(y=np.array(raw).astype('float'),
                                                sr=sample_rate,
                                                hop_length=hop_length)
            t = librosa.times_like(oenv, sr=sample_rate, hop_length=hop_length)
            self.onset_list.append(oenv)
            self.time_list.append(t)
            
    def compute_intensities(self):
        print("Computing intensities...")
        self.intensity_list = []
        for raw in tqdm(self.raw_list):
            intensity = []
            base = 0
            while base < len(raw):
                intensity.append(np.max(np.abs(raw[base:base+hop_length])))
                base += hop_length
            self.intensity_list.append( np.array(intensity).astype('float') )

    # return true if a is newer or same age than b, else false
    def is_newer(self, a, b):
        if os.path.exists(a) and os.path.exists(b):
            stat_a = os.stat(a)
            mtime_a = stat_a.st_mtime
            stat_b = os.stat(b)
            mtime_b = stat_b.st_mtime
            if mtime_a >= mtime_b:
                return True
        return False

    def compute_clarities(self):
        cache_dir = self.check_cache()
        
        log("Computing clarities...")
        self.clarity_list = []
        self.chroma_list = []
        for i, raw in enumerate(tqdm(self.raw_list)):
            # check cache
            fullname = os.path.join(self.path, self.name_list[i])
            name = os.path.basename(self.name_list[i])
            basename, ext = os.path.splitext(name)
            cachename = os.path.join(self.path, "cache",
                                     basename + ".clarity")
            if self.is_newer(cachename, fullname):
                # load from cache
                #print("loading from cache:", cachename)
                with open(cachename, "rb") as f:
                    clarity = np.load(f)
            else:
                # compute
                chroma = librosa.feature.chroma_cqt(y=np.array(raw).astype('float'),
                                                    sr=sample_rate,
                                                    hop_length=hop_length)
                self.chroma_list.append(chroma)
                a = len(self.time_list[i])
                b = len(self.intensity_list[i])
                c = chroma.shape[1]
                min = np.min([a, b, c])
                notes = np.zeros(min)
                clarity = np.zeros(min)
                imax = np.max(self.intensity_list[i])
                for j in range(min):
                    notes[j] = np.argmax(chroma[:,j]) * (self.intensity_list[i][j] / imax)
                    clarity[j] = (chroma[:,j] < 0.2).sum() * self.intensity_list[i][j]
                self.note_list.append(notes.T)
                clarity = clarity.T
                # save in cache
                #print("saving clarity as:", cachename)
                with open(cachename, "wb") as f:
                    np.save(f, clarity.T)
            self.clarity_list.append(clarity)

    def compute_rms(self):
        # compute an rms metric for track, but just over the areas
        # where clarity > threshold
        log("Estimating rms for active regions:")
        self.rms_list = []
        for i in range(len(self.clarity_list)):
            clarity = self.clarity_list[i]
            intensity = self.intensity_list[i]
            # 3print("track:", i, len(clarity), len(intensity))
            mean = np.mean(clarity)
            std = np.std(clarity)
            threshold = std * 0.1
            sum = 0
            count = 0
            for j in range(len(clarity)):
                if clarity[j] >= threshold:
                    sum += intensity[j]*intensity[j]
                    count += 1
            if count > 0:
                self.rms_list.append( math.sqrt(sum / count) )
            else:
                self.rms_list.append( 0 )
        log("rms:", self.rms_list)
        
    def compute_envelopes(self):
        self.envelope_list = []
        self.suppress_list = []
        
        # presumes clarities have been computed
        dt = self.time_list[0][1] - self.time_list[0][0]
        for i in range(len(self.clarity_list)):
            clarity = self.clarity_list[i]
            times = self.time_list[i]
            env = []
            commands = []
            print("track:", i, len(clarity), len(times))
            mean = np.mean(clarity)
            std = np.std(clarity)
            threshold = std * 0.1
            start = 0
            end = 0
            active = None
            for j in range(len(clarity)):
                if clarity[j] < threshold:
                    if active is None:
                        # starting inactive
                        env.append( [times[j], 0] )
                    elif active:
                        # just entered a dead spot
                        #print(" active:", active, start, end)
                        env.append( [times[j], 1] )
                        start = j
                    active = False
                else:
                    if active is None:
                        # starting active
                        env.append( [times[j], 1] )
                    elif not active:
                        # just entered a live spot
                        commands.append([times[start], times[end]])
                        # shape the dead spot env
                        #print(" active:", active, start, end)
                        if (end - start)*dt >= 0.2:
                            p1 = start + int(round(0.1/dt))
                            p2 = end - int(round(0.1/dt))
                            env.append( [times[p1], 0] )
                            env.append( [times[p2], 0] )
                        else:
                            mid = int((end + start)*0.5)
                            env.append( [times[mid], 0] )
                        env.append( [times[end], 1] )
                        start = j
                    active = True
                end = j
            #print(" active:", active, start, end)
            if active:
                env.append( [times[-1], 1] )
            else:
                if (end - start)*dt >= 0.1:
                    p1 = start + int(round(0.1/dt))
                    env.append( [times[p1], 0] )
                env.append( [times[-1], 0] )
            #print(env)
            self.envelope_list.append(env)
            #print(commands)
            self.suppress_list.append(commands)
            
    def compute_margins(self):
        # presumes onset envelopes and clarities have been computed
        dt = self.time_list[0][1] - self.time_list[0][0]
        #print("dt:", dt)
        
        # find the start time of the the first clear note
        first_note = [0] * len(self.clarity_list)
        lead_list = []
        for i in range(len(self.clarity_list)):
            clarity = self.clarity_list[i]
            accum = 0
            for j in range(len(clarity)):
                accum += clarity[j]
                #print(self.time_list[i][j], accum)
                if accum > 100000:
                    first_note[i] = j
                    lead_list.append(self.intensity_list[i][:j])
                    break
        print("first notes:", first_note)

        # ramp in/out
        n = int(0.5 / dt)
        for ll in lead_list:
            print(len(ll), n)
            if len(ll) > 2*n:
                for i in range(n):
                    ll[i] *= i/n
                    ll[-(i+1)] *= i/n
            else:
                # skip super short lead in, sorry this one will need to
                # get fixed by hand probably
                pass

    def pretty_print_offset_array(self, offsets):
        print(offsets.shape)
        print("offsets: ", end='')
        for i in range(offsets.shape[0]):
            print("%.3f " % offsets[i], end='')
        print()
            
    def mutual_offset_solver(self, offset_matrix):
        self.offset_list = []
        done = False
        count = 0
        offsets = offset_matrix[0,:]
        stds = np.zeros(offsets.shape[0])
        self.pretty_print_offset_array(offsets)
        while not done and count < 1000:
            done = True
            count += 1
            offsets_ss = np.copy(offsets)
            for i in range(offsets.shape[0]):
                diff_array = offsets_ss - offset_matrix[i,:]
                median = np.median(diff_array)
                mean = np.mean(diff_array)
                std = np.std(diff_array)
                offsets[i] = median
                stds[i] = std
                print(diff_array)
                print(median, mean, std)
            print("count:", count)
            self.pretty_print_offset_array(offsets)
            # decide if we need to do another iteration
            for i in range(offsets.shape[0]):
                if abs(offsets[i] - offsets_ss[i]) > 0.0005:
                    done = False
        log("Fit deviations (indicator of fit quality):")
        log(stds.tolist())
        # slide the solution by the median offset to keep it centered
        offsets -= np.median(offsets)
        return offsets                
 
    def correlate_mutual(self, metric_list, plot=False):
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
                    shift = len(metric_list[j]) - 1 - max_index
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

        # if False:
        #     self.offset_list = []
        #     for i in range(num):
        #         diff_array = offset_matrix[0,:] - offset_matrix[i,:]
        #         median = np.median(diff_array)
        #         print(offset_matrix[i,:])
        #         print(diff_array)
        #         print(median, np.mean(diff_array), np.std(diff_array))
        #         self.offset_list.append(median)
        
        self.offset_list = self.mutual_offset_solver(offset_matrix).tolist()
        log("Track time offsets (sec):", self.offset_list)
        
    def mydiff(self, a, b):
        an = a.shape[0]
        bn = b.shape[0]
        pad = np.zeros(a.shape[0])
        b1 = np.concatenate((pad, b, pad), axis=None)
        result = []
        for i in range(an+bn):
            # print(i)
            diff = a - b1[i:i+an]
            result.append(np.sum(diff*diff))
        result = np.array(result)
        result = np.amax(result) - result
        return result
    
    def correlate_to_reference(self, ref_index, metric_list, plot=False):
        # compute relative time offsets by best correlation
        num = len(metric_list)
        self.offset_list = [0] * num
        for i in range(0, num):
            print(ref_index, i, metric_list[ref_index].shape, metric_list[i].shape)
            ycorr = np.correlate(metric_list[ref_index],
                                 metric_list[i],
                                 mode='full')
            #ycorr = self.mydiff(metric_list[ref_index], metric_list[i])
            max_val = np.amax(ycorr)
            max_index = np.argmax(ycorr)
            print("max index:", max_index)
            if max_index > len(metric_list[i]):
                shift = max_index - len(metric_list[i])
                shift_time = self.time_list[ref_index][shift]
                plot1 = metric_list[ref_index]
                plot2 = np.concatenate([np.zeros(shift),
                                        metric_list[i]])
                print(ref_index, i, self.time_list[ref_index][shift])
            elif max_index < len(metric_list[i]):
                shift = len(metric_list[i]) - max_index
                shift_time = -self.time_list[i][shift]
                plot1 = np.concatenate([np.zeros(shift),
                                        metric_list[ref_index]], axis=None)
                plot2 = metric_list[i]
                print(ref_index, -self.time_list[i][shift])
            else:
                plot1 = metric_list[ref_index]
                plot2 = metric_list[i]
                shift = 0
                shift_time = 0
                print(ref_index, 0)
            self.offset_list[i] = shift_time
            if plot:
                plt.figure()
                plt.plot(ycorr)
                plt.figure()
                plt.plot(plot1, label=ref_index)
                plt.plot(plot2, label=i)
                plt.legend()
                plt.show()
        print("offset_list:\n", self.offset_list)

    # sync by claps
    def sync_by_claps(self, plot=False):
        # presumes onset envelopes and clarities have been computed

        dt = self.time_list[0][1] - self.time_list[0][0]
        print("dt:", dt)
        
        # find the start time of the the first clear note
        first_note = [0] * len(self.clarity_list)
        lead_list = []
        for i in range(len(self.clarity_list)):
            clarity = self.clarity_list[i]
            mean = np.mean(self.clarity_list[i])
            std = np.std(self.clarity_list[i])
            accum = 0
            for j in range(len(clarity)):
                if clarity[j] > std * 0.25:
                    accum += clarity[j]
                    #print(self.time_list[i][j], accum)
                if accum > 100000:
                    first_note[i] = j
                    trim = int(round((1.0/dt)))
                    lead_list.append(self.intensity_list[i][:j-trim])
                    break
        print("first notes:", first_note)

        # ramp in/out
        n = int(0.5 / dt)
        for ll in lead_list:
            print(len(ll), n)
            if len(ll) > 2*n:
                for i in range(n):
                    ll[i] *= i/n
                    ll[-(i+1)] *= i/n
            else:
                # skip super short lead in, sorry this track will need
                # to get aligned by hand probably
                pass

        # smooth (spread out peaks so better chance of overlapping
        for i in range(len(lead_list)):
            box_pts = int(0.2/dt)
            box = np.ones(box_pts)/box_pts
            lead_list[i] = np.convolve(lead_list[i], box, mode='same')
            
        self.correlate_mutual(lead_list, plot=plot)

    def clean_noise(self, clean=0.2, reverb=0):
        cache_dir = self.check_cache()
        
        for i, sample in enumerate(self.sample_list):
            fullname = os.path.join(self.path, self.name_list[i])
            name = os.path.basename(self.name_list[i])
            basename, ext = os.path.splitext(name)
            canon_name = os.path.join(self.path, "cache",
                                      basename + "-canon.mp3")
            noise_name = os.path.join(self.path, "cache",
                                      basename + "-noise.mp3")
            noiseprof_name = os.path.join(self.path, "cache",
                                         basename + ".noiseprof")
            clean_name = os.path.join(self.path, "cache",
                                      basename + "-clean.mp3")
            log("Generating noise profile for:", name)
            if not self.is_newer(noise_name, canon_name):
                new_sample = None
                commands = self.suppress_list[i]
                if len(commands):
                    #print("commands:", commands)
                    blend = 100     # ms
                    seg = None
                    start = 0
                    for cmd in commands:
                        #print("command:", cmd)
                        (t0, t1) = cmd
                        ms0 = int(round(t0*1000))
                        ms1 = int(round(t1*1000))
                        #print("  start:", start, "range:", ms0, ms1)
                        if (ms1 - ms0) < 2*blend:
                            # too short to deal with
                            continue
                        #print("noise:", ms0, ms1)
                        noise = sample[ms0:ms1]
                        if new_sample is None:
                            new_sample = noise
                        else:
                            new_sample.append(noise, crossfade=blend)
                if not new_sample is None:
                    # generate noise sample
                    new_sample.export(noise_name, format="mp3")
            if os.path.exists(noise_name):
                if not self.is_newer(noiseprof_name, noise_name):
                    # generate noise profile
                    command = [ "sox", noise_name, "-n", "noiseprof",
                                noiseprof_name ]
                    log("command:", command)
                    result = call(command)
                    log("sox result code:", result)
            if os.path.exists(noiseprof_name):
                # generate cleaned up version of audio
                if not self.is_newer(clean_name, noiseprof_name):
                    command = [ "sox", canon_name, clean_name, "noisered",
                                noiseprof_name, "%0.2f" % clean ]
                    if reverb > 0:
                        command += [ "reverb", "%d" % reverb, "50", "75" ]
                    log("command:", command)
                    result = call(command)
                    log("sox result code:", result)
                else:
                    print(clean_name, "is newer than", noise_name)
            else:
                log("No noise profile, using original sample as the cleaned version:", clean_name)
                sample.export(clean_name, format="mp3")
                
    # visualize audio streams (using librosa functions)
    def gen_plots(self, names, sync_offsets=None):
        print("Generating basic clip waveform...")
        # plot basic clip waveforms
        fig, ax = plt.subplots(nrows=len(self.raw_list),
                               sharex=True, sharey=True)
        for i in range(len(self.raw_list)):
            if sync_offsets is None:
                trimval = 0
            else:
                trimval = int(round(sync_offsets[i] * sample_rate / 1000))
            librosa.display.waveplot(np.array(self.raw_list[i][trimval:]).astype('float'), sr=sample_rate, ax=ax[i])
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
        fig, ax = plt.subplots(nrows=len(self.raw_list),
                               sharex=True, sharey=True)
        for i in range(len(self.raw_list)):
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
            fig, ax = plt.subplots(nrows=len(self.raw_list),
                                   sharex=True, sharey=True)
            for i in range(len(self.raw_list)):
                print(" ", names[i])
                if sync_offsets is None:
                    trimval = 0
                else:
                    trimval = int(round(sync_offsets[i] * sample_rate / 1000))
                img = librosa.display.specshow(self.chroma_list[i],
                                               x_axis='time',
                                               y_axis='chroma',
                                               hop_length=int(hop_length*0.5), ax=ax[i])
                ax[i].set(title='Chroma Representation of ' + names[i])
            fig.colorbar(img, ax=ax)

            print("Note clarity plot...")
            fig, ax = plt.subplots(nrows=len(self.raw_list),
                                   sharex=True, sharey=True)
            for i in range(len(self.raw_list)):
                a = len(self.time_list[i])
                c = self.clarity_list[i].shape[0]
                min = np.min([a, b, c])
                mean = np.mean(self.clarity_list[i])
                std = np.std(self.clarity_list[i])                
                print(i, len(self.time_list[i]), len(self.intensity_list[i]),
                      self.chroma_list[i].shape[1]) 
                ax[i].plot(self.time_list[i][:min], self.clarity_list[i][:min])
                max = np.max(self.clarity_list[i])
                if not self.envelope_list is None:
                    env = np.array(self.envelope_list[i]).astype('float').T
                    ax[i].plot(env[0,:], env[1,:]*max)
                ax[i].hlines(y=mean, xmin=0, xmax=1)
                ax[i].hlines(y=std, xmin=0, xmax=1)
       
        plt.show()
