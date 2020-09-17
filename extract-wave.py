#!/usr/bin/env python3

import argparse
import os

parser = argparse.ArgumentParser(description='extract wave file from anything ffmpeg can grok')
parser.add_argument('videos', metavar='videos', nargs='+', help='input videos')
args = parser.parse_args()

for v in args.videos:
    basename, ext = os.path.splitext(v)
    wavefile = basename + ".wav"
    if not os.path.exists(wavefile):
        print(v, basename, ext)
        command = "ffmpeg -i %s -map 0:1 -acodec pcm_s16le -ac 2 %s" % (v, wavefile)
        os.system(command)
