import csv
import lxml.etree as ET
import os

from .logger import log
from . import scan

# keep in mind:

# (1) Audacity imports the original sample and keeps it's own copy
# from then on.  (2) The aup file only references tracks by basename
# with no extension.  (3) If you import files from a hierarchy, or and
# the same name or basename exists, there is no way to determine from
# just looking at the aup file which of the original samples is being
# referenced. (4) if you use audacity to manually adjust timing syncs
# of tracks, please do not change the order of the tracks in audacity
# or the original project, this could cause mysterious timing issues
# that are hard to track down.
def sanity_check(audio_tracks):
    ok = True
    for i in range(len(audio_tracks)-1):
        for j in range(i + 1, len(audio_tracks)):
            head1, tail1 = os.path.split(audio_tracks[i])
            head2, tail2 = os.path.split(audio_tracks[j])
            base1, ext1 = os.path.splitext(tail1)
            base2, ext2 = os.path.splitext(tail2)
            if base1 == base2:
                ok = False
                log("Caution: multiple files have same root name.")
                log("    -->", audio_tracks[i])
                log("    -->", audio_tracks[j])
                #log("    If you are using audacity to fix sync:")
                #log("    Do not change any track ordering in your folder layout or audacity ...")
                #log("    or you could get really strange sync issues!")
    return ok
            
def offsets_from_aup(audio_tracks, audio_samples, dir, file):
    sanity_check(audio_tracks)
    
    sync_offsets = [None] * len(audio_tracks)
    filename = os.path.join(dir, file)
    xml = ET.parse(filename)
    project = xml.getroot()
    print(project.tag)
    for wt in project.iter('{*}wavetrack'):
        #localname = ET.QName(wt.tag).localname
        #print(localname)
        basename = wt.attrib["name"]
        rate = float(wt.attrib["rate"])
        wc = wt.find('{*}waveclip')
        offset = float(wc.attrib["offset"])
        seq = wc.find('{*}sequence')
        numsamp = int(seq.attrib["numsamples"])
        length = numsamp / rate
        print(basename, offset, length)
        for i, name in enumerate(audio_tracks):
            name = os.path.basename(name)
            if name.startswith(basename + "."):
                print("possible match:", name, len(audio_samples[i])/1000, length)
                if abs(len(audio_samples[i])/1000 - length) < 0.1:
                    log("  match:", name, len(audio_samples[i])/1000, length)
                    sync_offsets[i] = -offset * 1000 # ms
    # check for any missing offsets
    for i, name in enumerate(audio_tracks):
        if sync_offsets[i] is None:
            log("Warning, no sync value found for:", name)
            log("  Setting default sync time offset to 0.0")
            sync_offsets[i] = 0.0
    print(sync_offsets)
    return sync_offsets

def parse_aup(aup_file, dir_offset, pretty_path):
    offsets = {}
    xml = ET.parse(aup_file)
    project = xml.getroot()
    print(project.tag)
    for wt in project.iter('{*}wavetrack'):
        #localname = ET.QName(wt.tag).localname
        #print(localname)
        basename = wt.attrib["name"]
        rate = float(wt.attrib["rate"])
        wc = wt.find('{*}waveclip')
        offset = float(wc.attrib["offset"])
        seq = wc.find('{*}sequence')
        numsamp = int(seq.attrib["numsamples"])
        length = numsamp / rate
        print(basename, offset+dir_offset, length)
        offsets[os.path.join(pretty_path, basename)] = {
            "offset": offset+dir_offset,
            "length": length
        }
    print("offsets:", offsets)
    return(offsets)
    
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
        audio_tracks, video_tracks, aup_file = scan.scan_directory(dir)
        aup_file = scan.find_extension(dir, "aup")
        if aup_file:
            print(" ", aup_file)
            result = parse_aup(aup_file, dir_offset, pretty_path)
            offsets.update( result )
        else:
            # better find a .lof file
            result = parse_lof( os.path.join(dir, "audacity_import.lof"),
                                dir_offset, pretty_path )
            offsets.update( result )
    print("OFFSETS:", offsets)
    return offsets
