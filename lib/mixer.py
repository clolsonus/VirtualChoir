import math
import numpy as np
import os
from pydub import AudioSegment, playback  # pip install pydub
import random

from .logger import log

def combine(names, samples, sync_offsets, mute_tracks,
            hints={}, pan_range=0, suppress_list=None):
    durations_ms = []
    for i, sample in enumerate(samples):
        # print(names[i], len(sample) / 1000, sync_offsets[i])
        durations_ms.append( len(sample) - sync_offsets[i] )
    duration_ms = np.median(durations_ms)
    log("median audio duration (sec):", duration_ms / 1000)

    if not suppress_list is None:
        log("NOTICE: performing noise surpression on individual tracks.")
        
    # auto mute reference tracks, but include accompaniment
    for name in names:
        print("checking:", name)
        if name in mute_tracks:
            # already muted
            pass
        elif "accompaniment" in name.lower():
            # let it through if it has accompaniment in name
            pass
        elif "reference" in name.lower():
            mute_tracks.append(name)
                
    y_mixed = None
    mixed_count = 0
    for i, sample in enumerate(samples):
        if names[i] in mute_tracks:
            log("skipping muted:", names[i])
            continue
        if sample is None:
            log("empty sample")
            continue
        basename = os.path.basename(names[i])
        if basename in hints and "gain" in hints[basename]:
            track_gain = hints[basename]["gain"]
        else:
            track_gain = 1.0
        mixed_count += track_gain
        if sync_offsets is None:
            sync_offset = 0
        else:
            sync_offset = sync_offsets[i]
        log(" ", names[i], "offset(sec):", sync_offset/1000,
            "gain:", track_gain)
        sample = sample.set_channels(2)
        if pan_range > 0.00001 and pan_range <= 1.0:
            sample = sample.pan( random.uniform(-pan_range, pan_range) )
        if suppress_list is None:
            sample = sample.fade_in(1000)
        elif len(suppress_list[i]) == 0:
            sample = sample.fade_in(1000)
        else:
            commands = suppress_list[i]
            print("commands:", commands)
            blend = 300         # ms
            seg = None
            start = 0
            for cmd in commands:
                print("command:", cmd)
                (t0, t1) = cmd
                ms0 = int(round(t0*1000))
                ms1 = int(round(t1*1000))
                print("  start:", start, "range:", ms0, ms1)
                if ms1 - ms0 < 2*blend:
                    continue
                if ms0 > start:
                    if start < blend:
                        clip = sample[start:ms0+blend]
                        print("clip:", start, ms0+blend)
                    else:
                        clip = sample[start-blend:ms0+blend]
                        print("clip:", start-blend, ms0+blend)
                    if seg is None:
                        seg = clip
                    else:
                        seg = seg.append(clip, crossfade=blend)
                print("silent:", ms0, ms1)
                clip = AudioSegment.silent(duration=ms1-ms0)
                if seg is None:
                    seg = clip
                else:
                    seg = seg.append(clip, crossfade=blend)
                start = ms1
            # catch the last segment
            if start < len(sample) - blend:
                if start == 0:
                    clip = sample[start:]
                else:
                    clip = sample[start-blend:]
                if seg is None:
                    seg = clip
                else:
                    seg = seg.append(clip, crossfade=blend)
            #print("lengths:", len(sample), len(seg))
            sample = seg
        sr = sample.frame_rate
        sync_ms = sync_offset
        if sync_ms >= 0:
            synced_sample = sample[sync_ms:]
        else:
            pad = AudioSegment.silent(duration=-sync_ms)
            synced_sample = pad + sample
        # trim end for length
        synced_sample = synced_sample[:duration_ms]
        synced_sample = synced_sample.fade_out(1000)
        samples[i] = synced_sample
        
        y = np.array(synced_sample.get_array_of_samples()).astype('double')
        print(i, "max:", np.max(y))
        #print(" ", y.shape)
        if y_mixed is None:
            y_mixed = y
        else:
            # extend y_mixed array length if needed
            if y_mixed.shape[0] < y.shape[0]:
                diff = y.shape[0] - y_mixed.shape[0]
                #print("extending accumulator by:", diff)
                y_mixed = np.concatenate([y_mixed, np.zeros(diff)], axis=None)
            elif y.shape[0] < y_mixed.shape[0]:
                diff = y_mixed.shape[0] - y.shape[0]
                #print("extending sample by:", diff)
                y = np.concatenate([y, np.zeros(diff)], axis=None)
            y_mixed += (y * track_gain)
    if mixed_count < 1:
        log("No unmuted audio tracks found.")
        return AudioSegment.silent(1000)
    print("total max:", np.max(y_mixed))
    min_div = np.max(y_mixed) / 32767
    if math.sqrt(mixed_count) > min_div:
        # balsy but good chance of working
        y_mixed /= math.sqrt(mixed_count)
    else:
        y_mixed /= min_div
    #y_mixed /= math.pow(mixed_count, 0.6) # slightly more conservative
    #y_mixed / len(mixed_count) # very conservative output levels
    y_mixed = np.int16(y_mixed)
    mixed = AudioSegment(y_mixed.tobytes(), frame_rate=sr, sample_width=2, channels=sample.channels)
    mixed.normalize()
    return mixed

# presumes the mixer has updated each sample with align/trim/pad and
# noise suppression if requested, so this function just writes those
# out without further modification.
def save_aligned(results_dir, names, samples, mute_tracks,):
    # first clean out any previous aligned_audio tracks in case tracks
    # have been updated or added or removed since the previous run.
    for file in sorted(os.listdir(results_dir)):
        if file.startswith("aligned_audio_"):
            fullname = os.path.join(results_dir, file)
            log("NOTICE: deleting file from previous run:", file)
            os.unlink(fullname)
        
    log("Writing aligned version of samples (padded/trimed)...", fancy=True)
    for i, sample in enumerate(samples):
        if names[i] in mute_tracks:
            log("skipping muted:", names[i])
            continue
        basename = os.path.basename(names[i])
        name, ext = os.path.splitext(basename)
        # FilemailCli can't handle "," in file names
        name = name.replace(',', '')
        output_file = os.path.join(results_dir, "aligned_audio_" + name + ".mp3")
        log(" ", "aligned_audio_" + name + ".mp3")
        sample.export(output_file, format="mp3")
    
