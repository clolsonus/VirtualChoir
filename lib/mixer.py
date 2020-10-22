import math
import numpy as np
import os
from pydub import AudioSegment, playback  # pip install pydub
import random

def combine(names, samples, sync_offsets, mute_tracks,
            gain_hints={}, pan_range=0):
    durations_ms = []
    for i, sample in enumerate(samples):
        print(names[i], len(sample) / 1000, sync_offsets[i])
        durations_ms.append( len(sample) - sync_offsets[i] )
    duration_ms = np.median(durations_ms)
    print("median audio duration (ms):", duration_ms)
    
    y_mixed = None
    mixed_count = 0
    for i, sample in enumerate(samples):
        if names[i] in mute_tracks:
            print("skipping muted:", names[i])
            continue
        if os.path.basename(names[i]) in gain_hints:
            track_gain = gain_hints[os.path.basename(names[i])]
        else:
            track_gain = 1.0
        mixed_count += track_gain
        if sync_offsets is None:
            sync_offset = 0
        else:
            sync_offset = sync_offsets[i]
        print(" ", names[i], "offset(ms):", sync_offset, "gain:", track_gain)
        sample = sample.set_channels(2)
        if pan_range > 0.00001 and pan_range <= 1.0:
            sample = sample.pan( random.uniform(-pan_range, pan_range) )
        sample = sample.fade_in(1000)
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
        
        y = np.array(synced_sample.get_array_of_samples()).astype('double')
        #if sample.channels == 2:
        #    y = y.reshape((-1, 2))
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
    y_mixed *= (1 / math.sqrt(mixed_count)) # balsy but good chance of working
    #y_mixed *= (1 / math.pow(mixed_count, 0.6)) # slightly more conservative
    #y_mixed *= (1 / len(mixed_count)) # very conservative output levels
    y_mixed = np.int16(y_mixed)
    mixed = AudioSegment(y_mixed.tobytes(), frame_rate=sr, sample_width=2, channels=sample.channels)
    mixed.normalize()
    return mixed
    
def save_aligned(project, names, samples, sync_offsets, mute_tracks,):
    print("Writing aligned version of samples (padded/trimed)...")
    for i, sample in enumerate(samples):
        if names[i] in mute_tracks:
            print("skipping muted:", names[i])
            continue
        if sync_offsets is None:
            sync_offset = 0
        else:
            sync_offset = sync_offsets[i]
        sample = sample.set_channels(2)
        sr = sample.frame_rate
        sync_ms = sync_offset
        if sync_ms >= 0:
            synced_sample = sample[sync_ms:]
        else:
            pad = AudioSegment.silent(duration=-sync_ms)
            synced_sample = pad + sample
        basename = os.path.basename(names[i])
        name, ext = os.path.splitext(basename)
        output_file = os.path.join(project, "aligned_" + name + ".wav")
        print(" ", output_file, "offset(ms):", sync_offset)
        synced_sample.export(output_file, format="wav")
    
