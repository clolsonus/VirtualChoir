#!/usr/bin/env python3

import argparse

from services import common
from services import gdrive

parser = argparse.ArgumentParser(description='google folder public url')
parser.add_argument('url', help='google drive folder url')
args = parser.parse_args()

gd = gdrive.gdrive()
gd.sync_folder(args.url)
