#!/usr/bin/env python3

import argparse
import librosa                  # pip install librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
import os
#from pydub import AudioSegment, playback, scipy_effects  # pip install pydub
from tqdm import tqdm

from lib import analyze
from lib import aup
from lib import hints
from lib import logger
from lib.logger import log
from lib import mixer
from lib import scan
from lib import video

parser = argparse.ArgumentParser(description='virtual choir')
parser.add_argument('project', help='project folder')
parser.add_argument('--sync', default='clarity', choices=['clarity', 'clap'],
                    help='sync strategy')
parser.add_argument('--reference', help='file name of declared refrence track')
parser.add_argument('--suppress-noise', action='store_true', help='try to suppress extraneous noises.')
parser.add_argument('--write-aligned-tracks', action='store_true', help='write out padded/clipped individual tracks aligned from start.')
parser.add_argument('--mute-videos', action='store_true', help='mute all video tracks (some projects do all lip sync videos.')
parser.add_argument('--no-video', action='store_true', help='skip the video production.')
parser.add_argument('--resolution', default='1080p',
                    choices=['480p', '720p', '1080p', '1440p'],
                    help='video output resolution')
parser.add_argument('--rows', type=int, help='request specific number of video rows')
parser.add_argument('--fit', default='face', choices=['fit', 'zoom', 'face'],
                    help='video scaling/cropping strategy')
args = parser.parse_args()

log("Begin processing job", fancy=True)
log("Command line arguments:", args)

work_dirs = scan.work_directories(args.project, order="bottom_up")
print("work dirs:", work_dirs)

all_audio_tracks, all_video_tracks = scan.recurse_directory(args.project)

title_page = scan.find_basename(args.project, "title")
if title_page:
    log("title page:", title_page)
credits_page = scan.find_basename(args.project, "credits")
if credits_page:
    log("credits page:", credits_page)
log("audio tracks:", all_audio_tracks)
log("video tracks:", all_video_tracks)

#if aup_project:
#    print("audacity project for sync:", aup_project)

# load and accumulate hints for all dirs
hint_dict = {}
for dir in work_dirs:
    hint_dict.update( hints.load(dir) )
log("hints:", hint_dict)

# make results directory (if it doesn't exist)
results_dir = os.path.join(args.project, "results")
if not os.path.exists(results_dir):
    print("Creating:", results_dir)
    os.makedirs(results_dir)

# initialize logger
logger.init( os.path.join(results_dir, "report.txt") )

for dir in work_dirs:
    if dir == work_dirs[-1]:
        # last dir (top level)
        group_file = os.path.join(results_dir, "full-mix.mp3")
        clean = 0.1
        reverb = 40
        suppress_silent_zones = False
    else:
        group_file = os.path.join(dir + "-mix.mp3")
        clean = 0.25
        reverb = 0
        suppress_silent_zones = True
    #print("group_file:", group_file)
    if not scan.check_for_newer(dir, group_file):
        # nothing changed, so skip processing
        continue
    
    # load audio tracks, normalize, and resample at common (highest) sample rate
    audio_group = analyze.SampleGroup(dir)
    audio_group.scan()
    audio_group.load_samples()
    
    # generate mono version, set consistent sample rate, and filer for
    # analysis step
    audio_group.compute_raw()
    audio_group.compute_onset()
    audio_group.compute_intensities()
    audio_group.compute_clarities()
    audio_group.compute_envelopes()
    audio_group.clean_noise(clean=clean, reverb=reverb)

    print("aup:", audio_group.aup_file)
    if args.suppress_noise or not audio_group.aup_file:
        # we need to do a full analysis if we are asked to suppress noise
        # or we need to compute sync
        # audio_group.gen_plots(audio_tracks, sync_offsets=None)
        pass

    sync_offsets = []
    if not audio_group.aup_file:
        # let's figure out the autosync, fingers crossed!!!
        log("Starting automatic track alignment process...", fancy=True)

        log("Correlating audio samples")
        if args.reference:
            ref_index = -1
            for i, name in enumerate(audio_group.name_list):
                if name.endswith(args.reference):
                    ref_index = i
                    print("found reference track, index:", i)
            if ref_index < 0:
                print("Unable to match reference track name, giving up.")
                quit()
            audio_group.correlate_to_reference(ref_index, audio_group.clarity_list, plot=True)
            #audio_group.correlate_to_reference(ref_index, audio_group.note_list, plot=True)
        elif args.sync == "clarity":
            log("Sync by mutual best fit")
            audio_group.correlate_mutual(audio_group.clarity_list, plot=False)
        elif args.sync == "clap":
            log("Sync by lead in claps")
            audio_group.sync_by_claps(plot=False)

        log("Generating audacity_import.lof file")
        with open(os.path.join(dir, "audacity_import.lof"), 'w') as fp:
            for i in range(len(audio_group.offset_list)):
                fp.write('file "%s" offset %.3f\n' % (audio_group.name_list[i], audio_group.offset_list[i]))
        for i in range(len(audio_group.offset_list)):
            sync_offsets.append( -audio_group.offset_list[i] * 1000) # ms units
    else:
        # we found an audacity project, let's read the sync offsets from that
        log("Found an audacity project file, using that for time syncs:",
            audio_group.aup_file, fancy=True)
        sync_offsets = aup.offsets_from_aup(audio_group.name_list,
                                            audio_group.sample_list,
                                            dir, audio_group.aup_file)

    log("Mixing samples...", fancy=True)

    if args.mute_videos:
        log("Reqeust to mute the audio channels on videos: lip sync mode.")
        mute_tracks = audio_group.video_list
    else:
        mute_tracks = []
    mixed = mixer.combine(audio_group, sync_offsets,
                          mute_tracks, hints=hint_dict, pan_range=0.3,
                          suppress_silent_zones=suppress_silent_zones)
    log("Mixed audio file:", group_file)
    mixed.export(group_file, format="mp3", tags={'artist': 'Various artists', 'album': 'Best of 2011', 'comments': 'This album is awesome!'})

    if args.write_aligned_tracks:
        log("Generating trimmed/padded tracks that start at a common aligned time.")
        # write trimmed/padded samples for 'easy' alignment
        mixer.save_aligned(results_dir, audio_group.name_list,
                           audio_group.sample_list, mute_tracks)

if len(all_video_tracks) and not args.no_video:
    offsets = aup.build_offset_map(args.project)
    
    log("Generating gridded video", fancy=True)
    video_offsets = []
    for track in all_video_tracks:
        trackbase, ext = os.path.splitext(track)
        if track in offsets:
            # from .lof file
            offset = offsets[track]["offset"]
        elif trackbase in offsets:
            # aup doesn't save ext
            offset = offsets[trackbase]["offset"]
        else:
            log("No offset found for:", track)
        print(track, offset)
        video_offsets.append(offset)
    if args.write_aligned_tracks:
        log("Generating trimmed/padded tracks that start at a common aligned time.")
        video.save_aligned(args.project, results_dir, all_video_tracks,
                           video_offsets)
    # render the new combined video
    video.render_combined_video( args.project, args.resolution, results_dir,
                                 all_video_tracks, video_offsets,
                                 hints=hint_dict, rows=args.rows, fit=args.fit,
                                 title_page=title_page,
                                 credits_page=credits_page )
    video.merge( args.project, results_dir )
    
else:
    log("No video tracks, or audio-only requested.")

log("End of processing.", fancy=True)
