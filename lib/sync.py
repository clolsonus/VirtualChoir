import csv
import json
import os

from .logger import log
from . import scan

def parse_lof(lof_file, dir_offset, pretty_path):
    if not os.path.exists(lof_file):
        log("Cannot find a .lof timing file, aborting:", lof_file)
        quit()
    offsets = {}
    with open(lof_file, 'r') as fp:
        reader = csv.reader(fp, delimiter=' ', skipinitialspace=True)
        for row in reader:
            print("|".join(row))
            if len(row) != 4:
                log("bad lof file syntax:", row)
                continue
            name = row[1]
            offsets[os.path.join(pretty_path, name)] = {
                "offset": float(row[3])+dir_offset,
                "length": None
            }
    print("offsets:", offsets)
    return(offsets)

def parse_json(json_file, dir_offset, pretty_path, audio_tracks=None):
    print("parse json:", json_file)
    if not os.path.exists(json_file):
        log("Cannot find the sync timing .json file, aborting:", json_file)
        quit()
    offsets = {}
    with open(json_file, 'r') as fp:
        info = json.load(fp)
        print(info)
        for row in info:
            if "name" in row and "start" in row and "end" in row:
                print(row["name"], row["start"])
                name = row["name"]
                start = row["start"]
                end = row["end"]
                secs = end - start
                if audio_tracks is not None:
                    for i, track_name in enumerate(audio_tracks):
                        if track_name.startswith(name + "."):
                            log("  match:", track_name)
                            offsets[os.path.join(pretty_path, track_name)] = {
                                "offset": float(start)+dir_offset
                            }
                else:
                    offsets[os.path.join(pretty_path, name)] = {
                        "offset": float(start)+dir_offset
                    }
            else:
                log("bad json sync file syntax:", json_file)
                log("entry:", row)
                quit()
    print("offsets:", offsets)
    return(offsets)

def build_offset_map(path):
    offsets = {}
    dirs = scan.work_directories(path, order="top_down")
    remove = len(dirs[0])            # hacky
    for dir in dirs: 
        pretty_path = dir[(remove+1):]
        print("remove:", dir, pretty_path)
        basename = os.path.basename(dir)
        print(pretty_path, len(pretty_path))
        if len(pretty_path):
            mixed_name = pretty_path + "-mix"
        else:
            mixed_name = basename + "-mix"
        print("mixed_name:", mixed_name)
        if mixed_name in offsets:
            dir_offset = offsets[mixed_name]["offset"]
        elif mixed_name + ".mp3" in offsets:
            dir_offset = offsets[mixed_name + ".mp3"]["offset"]
        else:
            dir_offset = 0.0
        print(dir, basename, dir_offset)
        sync_file = scan.find_extension(dir, "json")
        lof_file = scan.find_extension(dir, "lof")
        if sync_file:
            result = parse_json(sync_file, dir_offset, pretty_path)
        elif lof_file:
            result = parse_lof( lof_file, dir_offset, pretty_path )
            offsets.update( result )
        else:
            log("no sync source .lof or sync.json, can't continue with video:", dir)
            quit()
    print("OFFSETS:", offsets)
    return offsets
