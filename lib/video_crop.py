import cv2
import numpy as np

# return a scaled versino of the frame that fits
def get_fit(frame, scale_w, scale_h):
    if scale_w < scale_h:
        result = cv2.resize(frame, (0,0), fx=scale_w, fy=scale_w,
                            interpolation=cv2.INTER_AREA)
    else:
        result = cv2.resize(frame, (0,0), fx=scale_h, fy=scale_h,
                            interpolation=cv2.INTER_AREA)
    return result

# return a scaled versino of the frame that stretches vertically and
# is cropped (if needed) horizontally
def get_fit_height(frame, scale_h):
    result = cv2.resize(frame, (0,0), fx=scale_h, fy=scale_h,
                        interpolation=cv2.INTER_AREA)
    return result

def get_zoom(frame, scale_w, scale_h):
    if scale_w < scale_h:
        result = cv2.resize(frame, (0,0), fx=scale_h, fy=scale_h,
                            interpolation=cv2.INTER_AREA)
    else:
        result = cv2.resize(frame, (0,0), fx=scale_w, fy=scale_w,
                            interpolation=cv2.INTER_AREA)
    return result
        
def clip_frame(frame, cell_w, cell_h):
    (tmp_h, tmp_w) = frame.shape[:2]
    if tmp_h > cell_h:
        cuth = int((tmp_h - cell_h) * 0.5)
    else:
        cuth = 0
    if tmp_w > cell_w:
        cutw = int((tmp_w - cell_w) * 0.5)
    else:
        cutw = 0
    return frame[cuth:cuth+int(round(cell_h)),cutw:cutw+int(round(cell_w))]

# modifies bg
def overlay_frames(bg, fg):
    x = 0
    y = 0
    if fg.shape[1] < bg.shape[1]:
        gap = (bg.shape[1] - fg.shape[1]) * 0.5
        x += int(gap)
    if fg.shape[0] < bg.shape[0]:
        gap = (bg.shape[0] - fg.shape[0]) * 0.5
        y += int(gap)
    bg[y:y+fg.shape[0],x:x+fg.shape[1]] = fg
    return bg

def fit_face(v):
    (frameh, framew) = v.raw_frame.shape[:2]
    frame_ar = framew / frameh
    if v.face.count > 0:
        (x, y, w, h) = v.face.get_face()
    else:
        x = 0
        y = 0
        h = frameh
        w = framew
    v.raw_frame = cv2.rectangle(np.array(v.raw_frame), (x,y), (x+w,y+h),
                                (0,255,0), 2)
    #print(" ", x,y,w,h)

    # ideal shape to pad around face
    padw = w * 0.4
    padh = h * 0.4
    wantw = int(round(w + 2*padw))
    wanth = int(round(h + 3*padh))
    face_ar = wantw / wanth

    # expand our area to match the raw frame aspect ratio
    # if frame_ar < face_ar:
    #     # frame taller than face
    #     wanth = int(round( wantw / frame_ar))
    # else:
    #     wantw = int(round(wanth * frame_ar))

    # compute the upper corner to position the face
    wantx = x - int(round((wantw - w) * 0.5))
    wanty = y - int(round((wanth - h) * 0.333))

    # don't ask for more than the frame has
    if wantw > framew:
        wantw = framew
    if wanth > frameh:
        wanth = frameh
    if wantx < 0:
        wantx = 0
    if wantx + wantw > framew:
        wantx = framew - wantw
    if wanty < 0:
        wanty = 0
    if wanty + wanth > frameh:
        wanty = frameh - wanth
    # v.raw_frame = cv2.rectangle(np.array(v.raw_frame), (wantx,wanty), (wantx+wantw,wanty+wanth), (255,255,255), 2)
    #cv2.imshow(str(v.reader), v.raw_frame)

    # best fit we can make on the face with original aspect ratio
    crop = v.raw_frame[wanty:wanty+wanth, wantx:wantx+wantw]
    #cv2.imshow(str(v.reader) + " crop", crop)

    # now cram it into the available space (lossy/zoom)
    croph, cropw = crop.shape[:2]
    scale_h = v.size_h / croph
    final = get_fit_height(crop, scale_h)
    final = clip_frame(final, v.size_w, v.size_h)
    #cv2.imshow(str(v.reader) + " final", final)

    # shape_ar = v.size_w / v.size_h
    # print(
    #     "face ar: %.3f" % face_ar,
    #     "frame ar: %.3f" % frame_ar,
    #     "shape ar: %.3f" % shape_ar
    # )
    return final
        
 
