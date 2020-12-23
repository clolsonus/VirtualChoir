import os

from .logger import log

# find all the project clips (todo: recurse)
audio_extensions = [ "aac", "aif", "aiff", "m4a", "mp3", "ogg", "wav" ]
video_extensions = [ "avi", "m4v", "mov", "mp4", "qt", "webm" ]
audacity_extension = "aup"
ignore_extensions = [ "au", "lof", "txt", "zip" ]
ignore_files = [ "full-mix", "gridded_video", "mixed_audio", "silent_video" ]

# scan a directory for the things (does recurse)
def recurse_directory(path, pretty_path=""):
    audio_tracks = []
    video_tracks = []
    for file in sorted(os.listdir(path)):
        fullname = os.path.join(path, file)
        pretty_name = os.path.join(pretty_path, file)
        # print(pretty_name)
        if os.path.isdir(fullname):
            if file == "cache" or file == "results":
                pass
            else:
                a, v = recurse_directory(fullname, pretty_name)
                audio_tracks += a
                video_tracks += v
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
                # audacity project file
                pass
            else:
                print("Unknown extenstion (skipping):", file)
    return audio_tracks, video_tracks

# scan a directory for the things (does not recurse)
def scan_directory(path):
    audio_tracks = []
    video_tracks = []
    aup_project = None
    for file in sorted(os.listdir(path)):
        fullname = os.path.join(path, file)
        if os.path.isdir(fullname):
            # skip subdirectories
            pass
        else:
            basename, ext = os.path.splitext(file)
            if basename in ignore_files:
                continue
            if not len(ext) or ext[1:].lower() in ignore_extensions:
                continue
            if ext[1:].lower() in audio_extensions + video_extensions:
                audio_tracks.append(file)
                if ext[1:].lower() in video_extensions:
                    video_tracks.append(file)
            elif ext[1:].lower() == audacity_extension:
                if aup_project == None:
                    aup_project = file
            else:
                print("Unknown extenstion (skipping):", file)
    return audio_tracks, video_tracks, aup_project

# scan for nested work directories
def work_directories(path, order="bottom_up", pretty_path=""):
    dirs = []
    if path.endswith("/"):
        path = path[:-1]
    if order == "top_down":
        dirs.append(path)
    for file in sorted(os.listdir(path)):
        fullname = os.path.join(path, file)
        pretty_name = os.path.join(pretty_path, file)
        # print(pretty_name)
        if os.path.isdir(fullname):
            if file == "cache" or file == "results":
                pass
            elif file.endswith("_data"):
                # assume this is an audacity project dir
                log("Skipping audacity project dir:", pretty_name)
            else:
                dirs += work_directories(fullname, order, pretty_name)
    if order == "bottom_up":
        dirs.append( path )
    return dirs

# search path (does not recurse) for file with matching basename (case
# insensitive)
def find_basename(path, search):
    for file in sorted(os.listdir(path)):
        basename, ext = os.path.splitext(file)
        if basename.lower() == search:
            # return pretty name for convenience
            return os.path.join(path, file)
    return None

# search path (does not recurse) for file with matching basename (case
# insensitive)
def find_extension(path, search):
    for file in sorted(os.listdir(path)):
        basename, ext = os.path.splitext(file)
        if ext[1:].lower() == search:
            # return pretty name for convenience
            return os.path.join(path, file)
    return None

# return true if a is newer or same age than b, else false
def is_newer(a, b):
    if os.path.exists(a) and os.path.exists(b):
        stat_a = os.stat(a)
        mtime_a = stat_a.st_mtime
        stat_b = os.stat(b)
        mtime_b = stat_b.st_mtime
        if mtime_a > mtime_b:
            return True
    return False

# scan a directory for the things (does not recurse)
def check_for_newer(path, ref_file):
    if not os.path.exists(ref_file):
        print("no ref file, need to process")
        return True
    for file in sorted(os.listdir(path)):
        fullname = os.path.join(path, file)
        if os.path.isdir(fullname) and file == "results":
            # don't consider newer files in the results dir a reason
            # to flag a dependency is newer
            print("ignoring:", fullname)
        elif is_newer(fullname, ref_file):
            print(fullname, "is newer than", ref_file)
            return True
    return False
