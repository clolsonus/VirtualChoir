import math
import random

from .logger import log

class VideoSpiral:
    def __init__(self, videos, output_w, output_h, border):
        # plan the grid
        self.output_w = output_w
        self.output_h = output_h
        self.border = border
        self.place_count = 0
        self.maxt = 2 * math.pi
        num_portrait = 0
        num_landscape = 0
        for v in videos:
            if v is None or v.frame is None:
                continue
            (h, w) = v.frame.shape[:2]
            if w > h:
                num_landscape += 1
            else:
                num_portrait += 1
        self.cell_landscape = True
        if num_portrait > num_landscape:
            self.cell_landscape = False
            log("portrait dominant input videos")
        else:
            log("landscape dominant input videos")

        num_good_videos = sum(v is not None for v in videos)
        self.stept = self.maxt / num_good_videos
        log("video spriral, num vids:", num_good_videos, "step t:", self.stept)

    def update(self, videos, output_time):
        # compute placement/size for each frame (static grid strategy)
        cx = int(self.output_w / 2)
        cy = int(self.output_h / 2)
        sx = cx / (self.maxt*self.maxt)
        sy = cy / (self.maxt*self.maxt)
        for i, v in enumerate(videos):
            frame = v.raw_frame
            if v.frame is None:
                continue
            if v.raw_frame is None:
                pass
            elif v.place_x == None or v.place_y == None:
                # first appears, place in a random location
                if self.cell_landscape:
                    v.size_w = int(self.output_w / 4)
                    v.size_h = int(self.output_h / 4)
                else:
                    v.size_w = int(self.output_h / 4)
                    v.size_h = int(self.output_w / 4)
                v.place_x = random.randrange(self.output_w - int(v.size_w))
                v.place_y = random.randrange(self.output_h - int(v.size_h))
                v.sort_order = self.place_count
                self.place_count += 1
            else:
                # update location
                t = math.fmod(output_time*0.5 + v.sort_order*self.stept, self.maxt)
                if self.cell_landscape:
                    w = int(round((t/self.maxt) * (self.output_w/4)))
                    h = int(round((t/self.maxt) * (self.output_h/4)))
                else:
                    w = int(round((t/self.maxt) * (self.output_h/4)))
                    h = int(round((t/self.maxt) * (self.output_w/4)))
                x = int(round((t*t) * math.cos(t) * sx + cx - 0.5*w))
                y = int(round((t*t) * math.sin(t) * sy + cy - 0.5*h))
                dw = w - v.size_w
                dh = h - v.size_h
                v.size_w = w - int(dw * 0.9)
                v.size_h = h - int(dw * 0.9)
                dx = x - v.place_x
                dy = y - v.place_y
                v.place_x = x - int(dx * 0.8)
                v.place_y = y - int(dy * 0.8)
