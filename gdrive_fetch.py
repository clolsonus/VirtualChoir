#!/usr/bin/env python3

import argparse
import json
import lxml.etree as ET
import os

from services import common
from services import gdrive

parser = argparse.ArgumentParser(description='google folder public url')
parser.add_argument('url', help='google drive folder url')
args = parser.parse_args()

gdrive.sync_folder(args.url)
