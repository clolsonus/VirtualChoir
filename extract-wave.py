#!/usr/bin/env python3

# https://librosa.org/doc/latest/auto_examples/plot_music_sync.html#sphx-glr-auto-examples-plot-music-sync-py

# pyrubberband may offer a higher quality stretch/compress function

import argparse
import os

parser = argparse.ArgumentParser(description='virtual choir')
parser.add_argument('videos', metavar='videos', nargs='+',
                    help='input videos')
args = parser.parse_args()

for v in args.videos:
    basename, ext = os.path.splitext(v)
    wavefile = basename + ".wav"
    if not os.path.exists(wavefile):
        print(v, basename, ext)
        command = "ffmpeg -i %s -map 0:1 -acodec pcm_s16le -ac 2 %s" % (v, wavefile)
        os.system(command)
