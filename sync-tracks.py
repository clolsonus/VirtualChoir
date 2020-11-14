#!/usr/bin/env python3

import argparse
import csv
import librosa                  # pip install librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
import os
from pydub import AudioSegment, playback, scipy_effects  # pip install pydub
from tqdm import tqdm

from lib import analyze
from lib import aup
from lib import logger
from lib.logger import log
from lib import mixer
from lib import video

parser = argparse.ArgumentParser(description='virtual choir')
parser.add_argument('project', help='project folder')
parser.add_argument('--sync', default='clarity', choices=['clarity', 'clap'],
                    help='sync strategy')
parser.add_argument('--reference', help='file name of declared refrence track')
parser.add_argument('--mute-videos', action='store_true', help='mute all video tracks (some projects do all lip sync videos.')
parser.add_argument('--no-video', action='store_true', help='skip the video production.')
parser.add_argument('--write-aligned-tracks', action='store_true', help='write out padded/clipped individual tracks aligned from start.')

args = parser.parse_args()

# find all the project clips (todo: recurse)
audio_extensions = [ "aac", "aif", "aiff", "m4a", "mp3", "ogg", "wav" ]
video_extensions = [ "avi", "mov", "mp4", "webm" ]
audacity_extension = "aup"
ignore_extensions = [ "au", "lof", "txt", "zip" ]
ignore_files = [ "gridded_video", "mixed_audio", "silent_video" ]
audio_tracks = []
video_tracks = []
title_page = None
credits_page = None
aup_project = None

def scan_directory(path, pretty_path=""):
    global title_page
    global credits_page
    global aup_project
    for file in sorted(os.listdir(path)):
        fullname = os.path.join(path, file)
        pretty_name = os.path.join(pretty_path, file)
        # print(pretty_name)
        if os.path.isdir(fullname):
            if file == "cache" or file == "results":
                pass
            else:
                scan_directory(fullname, os.path.join(pretty_path, file))
        else:
            basename, ext = os.path.splitext(file)
            if basename in ignore_files:
                continue
            if not len(ext) or ext[1:].lower() in ignore_extensions:
                continue
            if ext[1:].lower() in audio_extensions + video_extensions:
                audio_tracks.append(pretty_name)
                if ext[1:].lower() in video_extensions:
                    video_tracks.append(pretty_name)
            elif ext[1:].lower() == audacity_extension:
                if aup_project == None and not pretty_path:
                    aup_project = pretty_name
                else:
                    if aup_project != None:
                        print("WARNING! More than one audacity project file (.aup) found")
                        print("Using first one found:", aup_project)
                    else:
                        print("WARNING! Ignoring .aup file found in subdirectory:", aup_project)
            elif basename.lower() == "title":
                title_page = pretty_name
            elif basename.lower() == "credits":
                credits_page = pretty_name
            else:
                print("Unknown extenstion (skipping):", file)

log("Begin processing job", fancy=True)

scan_directory(args.project)

if title_page:
    log("title page:", title_page)
if credits_page:
    log("credits page:", credits_page)
log("audio tracks:", audio_tracks)
log("video tracks:", video_tracks)

if aup_project:
    print("audacity project for sync:", aup_project)

hints_file = os.path.join(args.project, "hints.txt")
gain_hints = {}
rotate_hints = {}
if os.path.exists(hints_file):
    log("Found a hints.txt file, loading...")
    with open(hints_file, 'r') as fp:
        reader = csv.reader(fp, delimiter=' ', skipinitialspace=True)
        for row in reader:
            print("|".join(row))
            if len(row) < 2:
                print("bad hint.txt syntax:", row)
                continue
            name = row[0]
            hint = row[1]
            if hint == "gain":
                if len(row) == 3:
                    gain_hints[name] = float(row[2])
                else:
                    print("bad hint.txt syntax:", row)
            elif hint == "rotate":
                if len(row) == 3:
                    rotate_hints[name] = int(row[2])
                else:
                    print("bad hint.txt syntax:", row)
            else:
                print("hint unknown (or typo):", row)
else:
    log("no hints file found.")
    
# make results directory (if it doesn't exist)
results_dir = os.path.join(args.project, "results")
if not os.path.exists(results_dir):
    print("Creating:", results_dir)
    os.makedirs(results_dir)

# make cache directory (if it doesn't exist)
cache_dir = os.path.join(args.project, "cache")
if not os.path.exists(cache_dir):
    print("Creating:", cache_dir)
    os.makedirs(cache_dir)

# initialize logger
logger.init( os.path.join(results_dir, "report.txt") )

# load audio tracks and normalize
log("loading audio tracks...")
audio_samples = []
max_frame_rate = 0
for track in audio_tracks:
    basename, ext = os.path.splitext(track)
    path = os.path.join(args.project, track)
    if ext == ".aif":
        ext = ".aiff"
    sample = AudioSegment.from_file(path, ext[1:])
    sample = sample.set_channels(2) # force samples to be stereo
    sample = sample.set_sample_width(2) # force to 2 for this project
    sample = sample.normalize()
    if sample.frame_rate > max_frame_rate:
        max_frame_rate = sample.frame_rate
    log(" ", track, "rate:", sample.frame_rate, "channels:", sample.channels, "width:", sample.sample_width)
    audio_samples.append(sample)
    
log("max sample rate:", max_frame_rate)
for i, sample in enumerate(audio_samples):
    audio_samples[i] = audio_samples[i].set_frame_rate(max_frame_rate)
    
sync_offsets = []
if not aup_project:
    # let's figure out the autosync, fingers crossed!!!
    log("Starting automatic track alignment process...", fancy=True)
    
    # generate mono version, set consistent sample rate, and filer for
    # analysis step
    log("Analyzing audio tracks...")
    audio_raws = []
    for i, sample in enumerate(tqdm(audio_samples)):
        mono = audio_samples[i].set_channels(1) # convert to mono
        mono_filt = scipy_effects.band_pass_filter(mono, 130, 523) #C3-C5
        raw = mono_filt.get_array_of_samples()
        audio_raws.append(raw)

    # analyze audio streams (using librosa functions)
    audio_group = analyze.SampleGroup()
    audio_group.compute_basic(audio_samples, audio_raws)
    audio_group.compute_intensities(audio_raws)
    audio_group.compute_clarities(audio_samples, audio_raws)
    #audio_group.gen_plots(audio_samples, audio_raws, audio_tracks, sync_offsets=None)

    log("Correlating audio samples")
    if args.reference:
        ref_index = -1
        for i, name in enumerate(audio_tracks):
            if name.endswith(args.reference):
                ref_index = i
                print("found reference track, index:", i)
        if ref_index < 0:
            print("Unable to match reference track name, giving up.")
            quit()
        #audio_group.correlate_to_reference(ref_index, audio_group.clarity_list, plot=True)
        audio_group.correlate_to_reference(ref_index, audio_group.note_list, plot=True)
    elif args.sync == "clarity":
        log("Sync by mutual best fit")
        audio_group.correlate_mutual(audio_group.clarity_list, plot=False)
    elif args.sync == "clap":
        log("Sync by lead in claps")
        audio_group.sync_by_claps()

    log("Generating audacity_import.lof file")
    with open(os.path.join(results_dir, "audacity_import.lof"), 'w') as fp:
        for i in range(len(audio_group.offset_list)):
            fp.write('file "%s" offset %.3f\n' % (audio_tracks[i], audio_group.offset_list[i]))
    for i in range(len(audio_group.offset_list)):
        sync_offsets.append( -audio_group.offset_list[i] * 1000) # ms units
else:
    # we found an audacity project, let's read the sync offsets from that
    log("Found an audacity project file, using that for time syncs:",
        aup_project, fancy=True)
    sync_offsets = aup.offsets_from_aup(audio_tracks, audio_samples,
                                        args.project, aup_project)

log("Mixing samples...", fancy=True)

if args.mute_videos:
    log("Reqeust to mute the audio channels on videos: lip sync mode.")
    mute_tracks = video_tracks
else:
    mute_tracks = []
mixed = mixer.combine(audio_tracks, audio_samples, sync_offsets, mute_tracks,
                      gain_hints=gain_hints, pan_range=0.25)
group_file = os.path.join(results_dir, "mixed_audio.mp3")
log("Mixed audio file: mixed_audio.mp3")
mixed.export(group_file, format="mp3", tags={'artist': 'Various artists', 'album': 'Best of 2011', 'comments': 'This album is awesome!'})

if args.write_aligned_tracks:
    log("Generating trimmed/padded tracks that start at a common aligned time.")
    # write trimmed/padded samples for 'easy' alignment
    mixer.save_aligned(results_dir, audio_tracks, audio_samples, sync_offsets,
                       mute_tracks)

if len(video_tracks) and not args.no_video:
    log("Generating gridded video", fancy=True)
    video_offsets = []
    for track in video_tracks:
        ai = audio_tracks.index(track)
        print(track, ai, -sync_offsets[ai] / 1000)
        video_offsets.append( -sync_offsets[ai] / 1000 )
    # render the new combined video
    video.render_combined_video( args.project, results_dir,
                                 video_tracks, video_offsets,
                                 rotate_hints=rotate_hints,
                                 title_page=title_page,
                                 credits_page=credits_page )
    video.merge( results_dir )
    if args.write_aligned_tracks:
        log("Generating trimmed/padded tracks that start at a common aligned time.")
        video.save_aligned(args.project, results_dir, video_tracks, sync_offsets)
    
else:
    log("No video tracks, or audio-only requested.")

log("End of processing.", fancy=True)
