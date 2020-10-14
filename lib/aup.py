import lxml.etree as ET
import os

def offsets_from_aup(audio_tracks, dir, file):
    sync_offsets = [0] * len(audio_tracks)
    filename = os.path.join(dir, file)
    xml = ET.parse(filename)
    project = xml.getroot()
    print(project.tag)
    for wt in project.iter('{*}wavetrack'):
        #localname = ET.QName(wt.tag).localname
        #print(localname)
        basename = wt.attrib["name"]
        wc = wt.find('{*}waveclip')
        offset = float(wc.attrib["offset"])
        print(basename, offset)
        for i, name in enumerate(audio_tracks):
            if name.startswith(basename + "."):
                sync_offsets[i] = -offset * 1000 # ms
    print(sync_offsets)
    return sync_offsets
