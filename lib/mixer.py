import math
import numpy as np
from pydub import AudioSegment, playback  # pip install pydub
import random

def combine(names, samples, sync_offsets, pan_range=0, sync_jitter_ms=0):
    y_mixed = None
    for i, sample in enumerate(samples):
        if sync_offsets is None:
            sync_offset = 0
        else:
            sync_offset = sync_offsets[i]
        print(" ", names[i], sync_offset)
        sample = sample.set_channels(2)
        if pan_range > 0.00001 and pan_range <= 1.0:
            sample = sample.pan( random.uniform(-pan_range, pan_range) )
        sample = sample.fade_in(1000)
        sample = sample.fade_out(1000)
        sr = sample.frame_rate
        sync_ms = sync_offset
        if sync_ms >= 0:
            synced_sample = sample[sync_ms:]
        else:
            pad = AudioSegment.silent(duration=-sync_ms)
            synced_sample = pad + sample        
        y = np.array(synced_sample.get_array_of_samples()).astype('float')
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
            y_mixed += y
    #y_mixed *= (1 / len(samples)) # very conservative output levels
    y_mixed *= (1 / math.sqrt(len(samples))) # balsy but good chance of working
    y_mixed = np.int16(y_mixed)
    mixed = AudioSegment(y_mixed.tobytes(), frame_rate=sr, sample_width=2, channels=sample.channels)
    mixed.normalize()
    return mixed
    
