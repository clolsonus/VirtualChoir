import random

from .logger import log

class VideoGrid:
    def __init__(self, videos, output_w, output_h, border):
        # plan the grid
        self.output_w = output_w
        self.output_h = output_h
        self.border = border
        self.place_count = 0
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
        self.cols = 1
        self.rows = 1
        while self.cols * self.rows < num_good_videos:
            if self.cell_landscape:
                if self.cols <= self.rows:
                    self.cols += 1
                else:
                    self.rows += 1
            else:
                if self.cols < self.rows*4:
                    self.cols += 1
                else:
                    self.rows += 1
        log("video grid (self.rows x self.cols):", self.rows, "x", self.cols)
        self.grid_w = int(output_w / self.cols)
        self.grid_h = int(output_h / self.rows)
        self.cell_w = (output_w - self.border*(self.cols+1)) / self.cols
        self.cell_h = (output_h - self.border*(self.rows+1)) / self.rows
        cell_aspect = self.cell_w / self.cell_h
        print("  grid size:", self.grid_w, "x", self.grid_h)
        print("  cell size:", self.cell_w, "x", self.cell_h, "aspect:", cell_aspect)

    def update(self, videos, output_time):
        # compute placement/size for each frame (static grid strategy)
        row = 0
        col = 0
        if self.cols >= 2 and self.rows >= 2:
            random_start = True
        else:
            random_start = False
        for v in videos:
            frame = v.raw_frame
            if frame is None:
                pass
            elif random_start and (v.place_x == None or v.place_y == None):
                # first appears, place in a random location
                v.place_x = random.randrange(self.output_w - int(self.cell_w))
                v.place_y = random.randrange(self.output_h - int(self.cell_h))
                v.sort_order = self.place_count
                self.place_count += 1
            else:
                # update location
                x = int(round(self.border + col * (self.cell_w + self.border)))
                y = int(round(self.border + row * (self.cell_h + self.border)))
                if frame.shape[1] < self.cell_w:
                    gap = (self.cell_w - frame.shape[1]) * 0.5
                    x += int(gap)
                if frame.shape[0] < self.cell_h:
                    gap = (self.cell_h - frame.shape[0]) * 0.5
                    y += int(gap)
                if v.place_x is None or v.place_y is None:
                    v.place_x = x
                    v.place_y = y
                else:
                    dx = x - v.place_x
                    dy = y - v.place_y
                    v.place_x = x - int(dx * 0.8)
                    v.place_y = y - int(dy * 0.8)
            v.size_w = self.cell_w
            v.size_h = self.cell_h
            col += 1
            if col >= self.cols:
                col = 0
                row += 1
