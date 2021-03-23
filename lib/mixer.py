import math
import numpy as np
import os
from pydub import AudioSegment, playback  # pip install pydub
import random

from .logger import log

def combine(group, sync_offsets, mute_tracks,
            hints={}, pan_range=0, suppress_silent_zones=False):
    durations_ms = []
    for i, sample in enumerate(group.sample_list):
        # print(group.name_list[i], len(sample) / 1000, sync_offsets[i])
        durations_ms.append( len(sample) - sync_offsets[i] )
    duration_ms = np.median(durations_ms)
    log("median audio duration (sec):", duration_ms / 1000)

    if suppress_silent_zones:
        if not group.suppress_list is None:
            log("NOTICE: performing noise supression on individual tracks.")
        else:
            log("NOTICE: no silent zones defined for this group, cannot suppress them.")
    else:
        log("NOTICE: not suppressing silent zones in top level tracks by design.")

    log("temp mute tracks:", mute_tracks)
    
    # auto mute reference tracks, but include accompaniment
    for name in group.name_list:
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
    for i, file in enumerate(group.name_list):
        name = os.path.basename(group.name_list[i])
        basefile, ext = os.path.splitext(name)
        canon_name = os.path.join("cache", basefile + "-canon.mp3")
        clean_name = os.path.join("cache", basefile + "-clean.mp3")
        print("names:", canon_name, clean_name)
        sample = group.load(clean_name)
        if sample is None:
            sample = group.load(canon_name)
        if sample is None:
            log("cannot find cached canonical audio or cleaned audio, die!")
            quit()
        if group.name_list[i] in mute_tracks:
            log("skipping muted:", group.name_list[i])
            continue
        if sample is None:
            log("empty sample")
            continue
        basename = os.path.basename(group.name_list[i])
        if basename in hints and "gain" in hints[basename]:
            track_gain = hints[basename]["gain"]
        else:
            track_gain = 1.0
        mixed_count += track_gain
        if sync_offsets is None:
            sync_offset = 0
        else:
            sync_offset = sync_offsets[i]
        log(" ", group.name_list[i], "offset(sec):", sync_offset/1000,
            "gain:", track_gain)
        sample = sample.set_channels(2)
        if pan_range > 0.00001 and pan_range <= 1.0:
            sample = sample.pan( random.uniform(-pan_range, pan_range) )
        commands = []
        if not group.suppress_list is None:
            commands = group.suppress_list[i]
        # add hints (offset relative to track 0) to suppress list
        if basename in hints and "suppress" in hints[basename]:
            offset_sec = sync_offset/1000
            print(hints[basename]["suppress"])
            for cmd in hints[basename]["suppress"]:
                print(cmd)
                commands.append( (cmd[0]+offset_sec, cmd[1]+offset_sec) )
        sample = sample.fade_in(1000)
        if suppress_silent_zones and len(commands):
            # temporarily skip non-music suppression
            print("commands:", commands)
            blend = 100         # ms
            seg = None
            start = 0
            new_sample = None
            for cmd in commands:
                #print("command:", cmd)
                (t0, t1) = cmd
                ms0 = int(round(t0*1000))
                ms1 = int(round(t1*1000))
                #print("  start:", start, "range:", ms0, ms1)
                if ms1 - ms0 < 2*blend + 1:
                    # too short to deal with
                    continue
                begin = sample[:ms0+blend]
                #print("silent:", ms0, ms1)
                silent = AudioSegment.silent(duration=ms1-ms0)
                end = sample[ms1-blend:]
                new_sample = begin.append(silent, crossfade=blend)
                new_sample = new_sample.append(end, crossfade=blend)
            if not new_sample is None:
                # we processed some commands
                print("lengths:", len(sample), len(new_sample))
                sample = new_sample
                # renormalized in case we suppressed something crazy
                sample = sample.normalize()
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
        group.sample_list[i] = synced_sample
        
        y = np.array(synced_sample.get_array_of_samples()).astype('double')
        print(i, "max:", np.max(y))
        #print(" ", y.shape)
        if y_mixed is None:
            y_mixed = y * track_gain
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
    print("total min:", np.min(y_mixed))
    min_div = np.max(np.abs(y_mixed)) / 31000 # leave headroom for reverb
    if math.sqrt(mixed_count) > min_div:
        # balsy but good chance of working
        y_mixed /= math.sqrt(mixed_count)
    else:
        y_mixed /= min_div
    #y_mixed /= math.pow(mixed_count, 0.6) # slightly more conservative
    #y_mixed / len(mixed_count) # very conservative output levels
    print("mixed max:", np.max(np.abs(y_mixed)))
    y_mixed = np.int16(y_mixed)
    mixed = AudioSegment(y_mixed.tobytes(), frame_rate=sr, sample_width=2, channels=sample.channels)
    mixed.normalize()
    return mixed

def clear_aligned(results_dir):
    # clean out any previous aligned_audio tracks in case tracks have
    # been removed since the previous run.
    for file in sorted(os.listdir(results_dir)):
        if file.startswith("aligned_audio_"):
            fullname = os.path.join(results_dir, file)
            log("NOTICE: deleting file from previous run:", file)
            os.unlink(fullname)
    
# presumes the mixer has updated each sample with align/trim/pad and
# noise suppression if requested, so this function just writes those
# out without further modification.
def save_aligned(results_dir, names, samples, mute_tracks,):
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
    
