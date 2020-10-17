import lxml.etree as ET
import os

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
                print("Caution: multiple files have same root name.")
                print("    -->", audio_tracks[i])
                print("    -->", audio_tracks[j])
                print("    If you are using audacity to fix sync:")
                print("    Do not change any track ordering in your folder layout or audacity ...")
                print("    or you could get really strange sync issues!")
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
                    print("  match:", name, len(audio_samples[i])/1000, length)
                    sync_offsets[i] = -offset * 1000 # ms
    # check for any missing offsets
    for i, name in enumerate(audio_tracks):
        if sync_offsets[i] is None:
            print("Warning, no sync value found for:", name)
            print("  Setting default sync time offset to 0.0")
            sync_offsets[i] = 0.0
    print(sync_offsets)
    return sync_offsets
