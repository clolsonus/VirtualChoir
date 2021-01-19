import cv2
import json
import math
import numpy as np
import os
from pydub import AudioSegment
import skvideo.io               # pip install sk-video
from subprocess import call
from tqdm import tqdm

from .logger import log
from . import video_crop
from . import video_faces
from .video_track import VideoTrack
from .video_grid import VideoGrid
from .video_spiral import VideoSpiral

def gen_dicts(fps, quality="sane"):
    inputdict = {
        '-r': str(fps)
    }
    if quality == "sane":
        outputdict = {
            # See all options: https://trac.ffmpeg.org/wiki/Encode/H.264
            '-vcodec': 'libx264',  # use the h.264 codec
            '-pix_fmt': 'yuv420p', # support 'dumb' players
            '-crf': '17',          # visually lossless (or nearly so)
            '-preset': 'medium',   # default compression
            '-r': str(fps)         # fps
        }
    elif quality == "lossless":
        outputdict = {
            # See all options: https://trac.ffmpeg.org/wiki/Encode/H.264
            '-vcodec': 'libx264',  # use the h.264 codec
            '-pix_fmt': 'yuv420p', # support 'dumb' players
            '-crf': '0',           # set the constant rate factor to 0, (lossless)
            '-preset': 'veryslow', # maximum compression
            '-r': str(fps)         # fps
        }
    return inputdict, outputdict

# fixme: figure out why zooming on some landscape videos in some cases
#        doesn't always fill the grid cell (see Coeur, individual grades.) 
def render_combined_video(project, resolution, results_dir,
                          video_names, offsets, hints={}, rows=None,
                          crop='face',
                          title_page=None, credits_page=None):
    if resolution == '480p':
        output_w = 854
        output_h = 480
    elif resolution == '720p':
        output_w = 1280
        output_h = 720
    elif resolution == '1080p':
        output_w = 1920
        output_h = 1080
    elif resolution == '1440p':
        output_w = 2560
        output_h = 1440
    else:
        log("Unknown video resolution request:", resolution)
        output_w = 1920
        output_h = 1080
    output_fps = 30
    log("output video specs:", output_w, "x", output_h, "fps:", output_fps)

    # load/find face locations
    faces = video_faces.find_faces(project, video_names, hints)
    
    # load static pages if specified
    if title_page:
        log("adding a title page:", title_page)
        title_rgb = cv2.imread(os.path.join(project, title_page),
                               flags=cv2.IMREAD_ANYCOLOR|cv2.IMREAD_ANYDEPTH)
        title_frame = np.zeros(shape=[output_h, output_w, 3], dtype=np.uint8)
        (h, w) = title_rgb.shape[:2]
        scale_w = output_w / w
        scale_h = output_h / h
        if scale_w < scale_h:
            title_scale = cv2.resize(title_rgb, None, fx=scale_w,
                                     fy=scale_w,
                                     interpolation=cv2.INTER_AREA)
        else:
            title_scale = cv2.resize(title_rgb, None, fx=scale_h,
                                     fy=scale_h,
                                     interpolation=cv2.INTER_AREA)
        x = int((output_w - title_scale.shape[1]) / 2)
        y = int((output_h - title_scale.shape[0]) / 2)
        title_frame[y:y+title_scale.shape[0],x:x+title_scale.shape[1]] = title_scale
        #cv2.imshow("title", title_frame)
        
    credits_frame = np.zeros(shape=[output_h, output_w, 3], dtype=np.uint8)
    if credits_page:
        log("adding a credits page:", credits_page)
        credits_rgb = cv2.imread(os.path.join(project, credits_page),
                                 flags=cv2.IMREAD_ANYCOLOR|cv2.IMREAD_ANYDEPTH)
        (h, w) = credits_rgb.shape[:2]
        scale_w = output_w / w
        scale_h = output_h / h
        if scale_w < scale_h:
            credits_scale = cv2.resize(credits_rgb, None, fx=scale_w,
                                     fy=scale_w,
                                     interpolation=cv2.INTER_AREA)
        else:
            credits_scale = cv2.resize(credits_rgb, None, fx=scale_h,
                                     fy=scale_h,
                                     interpolation=cv2.INTER_AREA)
        x = int((output_w - credits_scale.shape[1]) / 2)
        y = int((output_h - credits_scale.shape[0]) / 2)
        credits_frame[y:y+credits_scale.shape[0],x:x+credits_scale.shape[1]] = credits_scale
        #cv2.imshow("credits", credits_frame)

    # open all the video clips and grab some quick stats
    videos = []
    durations = []
    for i, file in enumerate(video_names):
        v = VideoTrack()
        basename = os.path.basename(file)
        if basename in hints and "video_hide" in hints[basename]:
            log("not drawing video for:", file)
        else:
            path = os.path.join(project, file)
            if v.open(path):
                durations.append(v.duration + offsets[i])
            if not faces is None and basename in faces:
                v.face.data = faces[basename]
                v.face.update_interp()
            # hack to use faces data to fix duration on webm videos
            # that don't self report
            if v.duration <= 1 and not faces is None and basename in faces:
                v.duration = v.face.data[-1]["time"]
                v.total_frames = int(round(v.duration * v.fps))
                print("Updated video duration:", v.duration)
                durations[-1] = v.duration + offsets[i]
        videos.append(v)
        # else:
        #     # don't render but we still need a placeholder so videos
        #     # continue match offset time list by position
        #     videos.append(None)
    if len(durations) == 0:
        return
    duration = np.median(durations)
    duration += 4 # for credits/fade out
    log("median video duration (with fade to credits):", duration)
    
    if len(videos) == 0:
        return

    # plan and setup the grid
    options = { "frame_w": output_w,
                "frame_h": output_h,
                "spacing": 6,
                "pad_top": 0,
                "pad_bottom": 0,
                "pad_left": 0,
                "pad_right": 0,
                "rows": rows }
    grid = VideoGrid(videos, options)
    #spiral = VideoSpiral(videos, output_w, output_h, border)
    
    # open writer for output
    output_file = os.path.join(results_dir, "silent_video.mp4")
    inputdict, outputdict = gen_dicts(output_fps, "sane")
    writer = skvideo.io.FFmpegWriter(output_file, inputdict=inputdict, outputdict=outputdict)
    done = False
    output_time = 0
    pbar = tqdm(total=int(duration*output_fps), smoothing=0.05)
    while output_time <= duration:
        # fetch/update the frames for the current time step
        for i, v in enumerate(videos):
            if v.reader is None:
                continue
            basename = os.path.basename(video_names[i])
            #print("basename:", basename)
            rotate = 0
            video_shift = 0
            if basename in hints:
                if "rotate" in hints[basename]:
                    rotate = hints[basename]["rotate"]
                if "video_shift" in hints[basename]:
                    video_shift = hints[basename]["video_shift"]
                if "face_detect" in hints[basename]:
                    face_detect = hints[basename]["face_detect"]
            local_time = output_time - offsets[i] - video_shift
            v.get_frame(local_time, rotate)

        # compute placement/size for each video frame (static grid strategy)
        grid.update(videos, output_time)
        #spiral.update(videos, output_time)

        # scale/fit each frame to it's cell size
        for i in range(len(videos)):
            v = videos[i]
            if v.reader is None:
                continue
            frame = v.raw_frame
            if not frame is None:
                (h, w) = frame.shape[:2]
                vid_aspect = w/h
                vid_landscape = (vid_aspect >= 1)
                scale_w = v.size_w / w
                scale_h = v.size_h / h
                
                background = None
                if crop == "none":
                    v.shaped_frame = video_crop.get_fit(frame, scale_w, scale_h)
                elif crop == "fit":
                    if grid.cell_landscape != vid_landscape:
                        # background/wings full zoom
                        background = video_crop.get_zoom(frame, scale_w, scale_h)
                        background = cv2.blur(background, (43, 43))
                        background = video_crop.clip_frame(background,
                                                           v.size_w, v.size_h)
                        # foreground compromise zoom/fit/arrangement
                        avg = (scale_w + scale_h) * 0.5
                        scale_w = avg
                        scale_h = avg
                        #print("scale:", scale_w, scale_h)
                    frame_scale = video_crop.get_zoom(frame, scale_w, scale_h)
                    frame_scale = video_crop.clip_frame(frame_scale,
                                                        v.size_w, v.size_h)
                    if background is None:
                        v.shaped_frame = frame_scale
                    else:
                        v.shaped_frame = video_crop.overlay_frames(background, frame_scale)
                elif crop == "face":
                    basename = os.path.basename(video_names[i])
                    if basename in hints and "face_detect" in hints[basename]:
                        use_face = (hints[basename]["face_detect"] > 0.01)
                        if not use_face:
                            v.no_face()
                    v.shaped_frame = video_crop.fit_face(v)
                    if v.shaped_frame.shape[1] < v.size_w:
                        # need background fill
                        background = video_crop.get_zoom(frame,
                                                         scale_w, scale_h)
                        background = cv2.blur(background, (43, 43))
                        background = video_crop.clip_frame(background,
                                                           v.size_w, v.size_h)
                        v.shaped_frame = video_crop.overlay_frames(background, v.shaped_frame)
                # cv2.imshow(video_names[i], frame_scale)
            else:
                # bummer video with no frames?
                v.shaped_frame = None

        # draw the main frame
        main_frame = np.zeros(shape=[output_h, output_w, 3], dtype=np.uint8)

        # place each frame
        sorted_vids = sorted(videos, key=lambda x: x.sort_order)
        for v in sorted_vids:
            frame = v.shaped_frame
            if frame is None:
                continue
            nf = frame.copy()
            x = int(v.place_x)
            if x < 0:
                diff = -x
                if diff >= nf.shape[1]:
                    continue
                else:
                    nf = nf[:,diff:]
                    x = 0
            if x > output_w - nf.shape[1]:
                diff = x - (output_w - nf.shape[1])
                if diff >= nf.shape[1]:
                    continue
                else:
                    nf = nf[:,:-diff]
            y = int(v.place_y)
            #print("y:", y, "shape:", nf.shape[:2])
            if y < 0:
                diff = -y
                if diff >= nf.shape[0]:
                    continue
                else:
                    nf = nf[diff:,:]
                    y = 0
            if y >= output_h - nf.shape[0]:
                diff = y - (output_h - nf.shape[0])
                if diff >= nf.shape[0]:
                    continue
                else:
                    nf = nf[:-diff,:]
            main_frame[y:y+nf.shape[0],x:x+nf.shape[1]] = nf

        if title_page and output_time <= 5:
            if output_time < 4:
                alpha = 1
            elif output_time >= 4 and output_time <= 5:
                alpha = (5 - output_time) / (5 - 4)
            else:
                alpha = 0
            #print("time:", output_time, "alpha:", alpha)
            output_frame = cv2.addWeighted(title_frame, alpha, main_frame, 1 - alpha, 0)
        elif output_time >= duration - 5:
            if output_time >= duration - 4:
                alpha = 1
            elif output_time >= duration - 5 and output_time < duration - 4:
                alpha = 1 - ((duration - 4) - output_time) / (5 - 4)
            else:
                alpha = 0
            #print("time:", output_time, "alpha:", alpha)
            output_frame = cv2.addWeighted(credits_frame, alpha, main_frame, 1 - alpha, 0)
        else:
            output_frame = main_frame
        cv2.imshow("output", output_frame)
        cv2.waitKey(1)

        # write the frame as RGB not BGR
        writer.writeFrame(output_frame[:,:,::-1])
        
        output_time += 1 / output_fps
        pbar.update(1)
    pbar.close()
    writer.close()
    log("gridded video (only) file: silent_video.mp4")
    
def merge(project, results_dir):
    log("video: merging video and audio into final result: gridded_video.mp4")
    # use ffmpeg to combine the video and audio tracks into the final movie
    input_video = os.path.join(results_dir, "silent_video.mp4")
    input_audio = os.path.join(results_dir, "full-mix.mp3")
    output_video = os.path.join(results_dir, "gridded_video.mp4")
    result = call(["ffmpeg", "-i", input_video, "-i", input_audio, "-c:v", "copy", "-c:a", "aac", "-y", output_video])
    print("ffmpeg result code:", result)

# https://superuser.com/questions/258032/is-it-possible-to-use-ffmpeg-to-trim-off-x-seconds-from-the-beginning-of-a-video/269960
# ffmpeg -i input.flv -ss 2 -vcodec copy -acodec copy output.flv
#   -vcodec libx264 -crf 0

#ffmpeg -f lavfi -i color=c=black:s=1920x1080:r=25:d=1 -i testa444.mov -filter_complex "[0:v] trim=start_frame=1:end_frame=5 [blackstart]; [0:v] trim=start_frame=1:end_frame=3 [blackend]; [blackstart] [1:v] [blackend] concat=n=3:v=1:a=0[out]" -map "[out]" -c:v qtrle -c:a copy -timecode 01:00:00:00 test16.mov

def save_aligned(project, results_dir, video_names, sync_offsets):
    # first clean out any previous aligned_audio tracks in case tracks
    # have been updated or added or removed since the previous run.
    for file in sorted(os.listdir(results_dir)):
        if file.startswith("aligned_video_"):
            fullname = os.path.join(results_dir, file)
            log("NOTICE: deleting file from previous run:", file)
            os.unlink(fullname)
            
    log("Writing aligned version of videos...", fancy=True)
    for i, video in enumerate(video_names):
        print(video, sync_offsets[i])
        video_file = os.path.join(project, video)
        # decide trim/pad
        sync_ms = sync_offsets[i] * 1000
        if sync_offsets[i] < 0:
            trim_sec = -sync_offsets[i]
            pad_sec = 0
        else:
            trim_sec = 0
            pad_sec = sync_offsets[i]
        
        # scan video meta data for resolution/fps
        metadata = skvideo.io.ffprobe(video_file)
        #print(metadata.keys())
        if not "video" in metadata:
            log("No video frames found in:", video_file)
            continue
        print(json.dumps(metadata["video"], indent=4))
        fps_string = metadata['video']['@r_frame_rate']
        (num, den) = fps_string.split('/')
        fps = float(num) / float(den)
        codec = metadata['video']['@codec_long_name']
        w = int(metadata['video']['@width'])
        h = int(metadata['video']['@height'])
        if '@duration' in metadata['video']:
            duration = float(metadata['video']['@duration'])
        else:
            duration = 1
        total_frames = int(round(duration * fps))
        frame_counter = -1

        # pathfoo
        basename = os.path.basename(video)
        name, ext = os.path.splitext(basename)
        # FilemailCli can't handle "," in file names
        name = name.replace(',', '')
        tmp_video = os.path.join(results_dir, "tmp_video.mp4")
        tmp_audio = os.path.join(results_dir, "tmp_audio.mp3")
        output_file = os.path.join(results_dir, "aligned_video_" + name + ".mp4")
        log("aligned_video_" + name + ".mp4", "offset(sec):", sync_offsets[i])
        log("  fps:", fps, "codec:", codec, "size:", w, "x", h, "total frames:", total_frames)

        # open source
        reader = skvideo.io.FFmpegReader(video_file, inputdict={}, outputdict={})
        
        # open destination
        inputdict, outputdict = gen_dicts(fps, "sane")
        writer = skvideo.io.FFmpegWriter(tmp_video, inputdict=inputdict, outputdict=outputdict)

        # pad or trim
        pad_frames = 0
        if pad_sec > 0:
            pad_frames = int(round(fps*pad_sec))
            log("  pad (sec):", pad_sec, "frames:", pad_frames)
                
        trim_frames = 0
        if trim_sec > 0:
            trim_frames = int(round(fps*trim_sec))
            log("  trim (sec):", trim_sec, "frames:", trim_frames)
            for j in range(trim_frames):
                reader._readFrame() # discard

        # copy remainder of video
        pbar = tqdm(total=(total_frames+pad_frames-trim_frames), smoothing=0.05)
        while True:
            try:
                frame = reader._readFrame()
                if not len(frame):
                    frame = None
                else:
                    (h, w) = frame.shape[:2]
                    vid_aspect = w/h
                    vid_landscape = (vid_aspect >= 1)
                    scale_w = 1280 / w
                    scale_h = 720 / h
                    background = None
                    if not vid_landscape:
                        # background/wings full zoom
                        background = video_crop.get_zoom(frame, scale_w, scale_h)
                        background = cv2.blur(background, (43, 43))
                        background = video_crop.clip_frame(background,
                                                           1280, 720)
                        # foreground compromise zoom/fit/arrangement
                        avg = (scale_w + scale_h) * 0.5
                        scale_w = avg
                        scale_h = avg
                        #print("scale:", scale_w, scale_h)
                    frame = video_crop.get_zoom(frame, scale_w, scale_h)
                    frame = video_crop.clip_frame(frame, 1280, 720)
                    if background:
                        frame = video_crop.overlay_frames(background, frame)
            except:
                frame = None
            if frame is None:
                break
            else:
                while pad_frames:
                    black = frame * 0
                    writer.writeFrame(black)
                    pad_frames -= 1
                    pbar.update(1)
                writer.writeFrame(frame)
                pbar.update(1)
        writer.close()
        pbar.close()

        # load the audio (ignoring we already have it loaded somewhere else)
        basename, ext = os.path.splitext(video_file)
        sample = AudioSegment.from_file(video_file, ext[1:])
        if sync_ms < 0:
            synced_sample = sample[-sync_ms:]
        else:
            pad = AudioSegment.silent(duration=sync_ms)
            synced_sample = pad + sample
        synced_sample.export(tmp_audio, format="mp3")
        
        log("video: merging aligned video and audio into final result:", output_file)
        # use ffmpeg to combine the video and audio tracks into the final movie
        input_video = os.path.join(results_dir, "tmp_video.mp4")
        input_audio = os.path.join(results_dir, "tmp_audio.mp3")
        result = call(["ffmpeg", "-i", input_video, "-i", input_audio, "-c:v", "copy", "-c:a", "aac", "-y", output_file])
        print("ffmpeg result code:", result)

        # clean up
        os.unlink(input_audio)
        os.unlink(input_video)
