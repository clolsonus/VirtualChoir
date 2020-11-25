import random

from .logger import log

class VideoGrid:
    def __init__(self, videos, output_w, output_h, border):
        # plan the grid
        self.output_w = output_w
        self.output_h = output_h
        self.border = border
        self.place_count = 0
        self.odd_offset = 0
        self.even_offset = self.output_w
        self.last_placed_row = 0
        num_portrait = 0
        num_landscape = 0
        for v in videos:
            if v.reader is None or v.frame is None:
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

        num_good_videos = sum(v.reader is not None for v in videos)
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
        if self.odd_offset >= 0:
            self.odd_offset = 0
        if self.even_offset < self.output_w:
            self.even_offset = self.output_w
        max_step = self.output_w * 0.010
        if self.cols >= 2 and self.rows >= 2:
            random_start = True
        else:
            random_start = False
        sorted_vids = sorted(videos, key=lambda x: x.sort_order)
        for v in sorted_vids:
            if v.reader is None:
                continue
            if v.raw_frame is not None:
                frame = v.raw_frame
                # target grid location
                x = self.border + col * (self.cell_w + self.border)
                y = self.border + row * (self.cell_h + self.border)
                # if frame.shape[1] < self.cell_w:
                #     gap = (self.cell_w - frame.shape[1]) * 0.5
                #     x += gap
                # if frame.shape[0] < self.cell_h:
                #     gap = (self.cell_h - frame.shape[0]) * 0.5
                #     y += gap
                if v.place_x is None or v.place_y is None:
                    self.place_count += 1
                    v.sort_order = self.place_count
                    if row > self.last_placed_row:
                        self.last_placed_row = row
                        self.even_offset = self.output_w
                    if v.place_x is None:
                        if True or row % 2 == 0:
                            v.place_x = self.even_offset
                            self.even_offset += (self.cell_w + self.border)
                        else:
                            self.odd_offset -= self.cell_w
                            v.place_x = self.odd_offset
                            self.odd_offset -= self.border
                    if v.place_y is None:
                        v.place_y = y
                else:
                    dx = (x - v.place_x) * 0.2
                    dy = (y - v.place_y) * 0.2
                    if dx > max_step: dx = max_step
                    if dx < -max_step: dx = -max_step
                    if dy > max_step: dy = max_step
                    if dy < -max_step: dy = -max_step
                    v.place_x += dx
                    v.place_y += dy
                v.size_w = self.cell_w
                v.size_h = self.cell_h
                col += 1
                if col >= self.cols:
                    col = 0
                    row += 1

        # outside videos loop!
        self.odd_offset += max_step
        self.even_offset -= max_step
