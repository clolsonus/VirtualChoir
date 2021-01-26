import cv2
import numpy as np

# return a scaled versino of the frame that fits
def get_fit(frame, scale_w, scale_h, cell_w, cell_h):
    cell = np.zeros(shape=[cell_h, cell_w, 3], dtype=np.uint8)
    if scale_w < scale_h:
        result = cv2.resize(frame, None, fx=scale_w, fy=scale_w,
                            interpolation=cv2.INTER_AREA)
    else:
        result = cv2.resize(frame, None, fx=scale_h, fy=scale_h,
                            interpolation=cv2.INTER_AREA)
    if cell_w > result.shape[1]:
        x = int((cell_w - result.shape[1])*0.5)
    else:
        x = 0
    if cell_h > result.shape[0]:
        y = int((cell_h - result.shape[0])*0.5)
    else:
        y = 0
    cell[y:y+result.shape[0],x:x+result.shape[1]] = result
    return cell

# return a scaled version of the frame that stretches vertically and
# is cropped (if needed) horizontally
def get_fit_height(frame, scale_h):
    result = cv2.resize(frame, None, fx=scale_h, fy=scale_h,
                        interpolation=cv2.INTER_AREA)
    return result

def get_zoom(frame, scale_w, scale_h):
    if scale_w < scale_h:
        result = cv2.resize(frame, None, fx=scale_h, fy=scale_h,
                            interpolation=cv2.INTER_AREA)
    else:
        result = cv2.resize(frame, None, fx=scale_w, fy=scale_w,
                            interpolation=cv2.INTER_AREA)
    return result
        
def clip_frame(frame, cell_w, cell_h):
    (tmp_h, tmp_w) = frame.shape[:2]
    if tmp_h > cell_h:
        cuth = int(round((tmp_h - cell_h) * 0.5))
    else:
        cuth = 0
    if tmp_w > cell_w:
        cutw = int(round((tmp_w - cell_w) * 0.5))
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
    if v.face.count > 0 and not v.local_time is None:
        (l, r, t, b) = v.face.get_face(v.local_time, 1.0)
    else:
        (b, r) = v.raw_frame.shape[:2]
        l = 0
        t = 0
    face_area = (r - l) * (b - t)
    cell_area = v.size_w * v.size_h
    if face_area < 2 * cell_area:
        # try something crazy (subpixel cropping by scaling up and
        # then back down)
        scale = 2.0
        superscale = cv2.resize(v.raw_frame, None, fx=scale, fy=scale,
                                interpolation=cv2.INTER_AREA)
        l = l * scale
        r = r * scale
        t = t * scale
        b = b * scale
    else:
        superscale = v.raw_frame
    (frameh, framew) = superscale.shape[:2]
    frame_ar = framew / frameh
    size_ar = v.size_w / v.size_h
        
    #v.raw_frame = cv2.rectangle(np.array(v.raw_frame), (x,y), (x+w,y+h), (0,255,0), 2)
    #print(" ", x,y,w,h)

    w = r - l
    h = b - t
    # ideal shape to pad around face
    padw = w * 0.5
    padh = h * 0.5 
    wanth = h + 3*padh
    wantw = wanth * size_ar + 1

    # expand our area to match the raw frame aspect ratio
    # if frame_ar < face_ar:
    #     # frame taller than face
    #     wanth = int(round( wantw / frame_ar))
    # else:
    #     wantw = int(round(wanth * frame_ar))

    # compute the upper corner to position the face
    wantl = l - (wantw - w) * 0.5
    wantt = t - (wanth - h) * 0.333

    # don't ask for more than the frame has
    wantl = int(round(wantl))
    wantt = int(round(wantt))
    wantw = int(round(wantw))
    wanth = int(round(wanth))
    if wantw > framew:
        wantw = framew
    if wanth > frameh:
        wanth = frameh
    if wantl < 0:
        wantl = 0
    if wantl + wantw > framew:
        wantl = framew - wantw
    if wantt < 0:
        wantt = 0
    if wantt + wanth > frameh:
        wantt = frameh - wanth
    # v.raw_frame = cv2.rectangle(np.array(v.raw_frame), (wantx,wanty), (wantx+wantw,wanty+wanth), (255,255,255), 2)
    #cv2.imshow(str(v.reader), v.raw_frame)

    # best fit we can make on the face with original aspect ratio
    crop = superscale[wantt:wantt+wanth, wantl:wantl+wantw]
    #cv2.imshow(str(v.reader) + " crop", crop)

    # now cram it into the available space (lossy/zoom)
    croph, cropw = crop.shape[:2]
    if croph == 0:
        # debug
        print("name:", v.file, "face:", l, r, t, b)
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
        
 
