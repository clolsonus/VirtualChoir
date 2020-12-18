import cv2
import json
import os
from tqdm import tqdm

from .logger import log
from .video_track import VideoTrack

# how many samples to take (more is better, but slower)
num_samples = 100

def find_faces(project, video_names, hints):
    # load any existing faces
    face_file = os.path.join(project, "results", "faces.json")
    if os.path.exists(face_file):
        with open(face_file, "r") as fp:
            faces = json.load(fp)
    else:
        faces = {}

    # let's find any missing faces
    for i, file in enumerate(video_names):
        basename = os.path.basename(file)
        if basename in faces:
            continue
        if basename in hints and "video_hide" in hints[basename]:
            log("not detecting faces in hidden video:", file)
            continue
        rotate = 0
        if basename in hints and "rotate" in hints[basename]:
            rotate = hints[basename]["rotate"]

        path = os.path.join(project, file)
        v = VideoTrack()
        if not v.open(path):
            log("cannot open video:", file)
            continue
        
        # walk through video by time
        pbar = tqdm(total=v.duration, smoothing=0.05)
        t = 0
        dt = v.duration / num_samples
        if dt < 1:
            # no more than onen sample a second
            dt = 1
        while not v.frame is None:
            v.get_frame(t, rotate)
            v.face.find_face(v.raw_frame)
            pbar.update(dt)
            t += dt
            cv2.waitKey(1)
        pbar.close()
        
        (l, r, t, b) = v.face.get_face()
        faces[basename] = { "left": l, "right": r,
                            "top": t, "bottom": b,
                            "count": v.face.count,
                            "miss": v.face.miss }
        
        # save/cache face location data (each iteration so we can
        # restart if needed)
        face_file = os.path.join(project, "results", "faces.json")
        with open(face_file, "w") as fp:
            json.dump(faces, fp, indent=4)

    # close our face preview window
    cv2.destroyAllWindows()
    
    return faces
