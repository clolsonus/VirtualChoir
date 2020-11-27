import math
import random

from .logger import log

class VideoGrid:
    def __init__(self, videos, output_w, output_h, border):
        log("Setting up the video grid:")
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
        log("Number of videos to place:", num_good_videos)
        if self.cell_landscape:
            self.num_rows = int(math.sqrt(num_good_videos))
            cols = self.num_rows
            remainder = num_good_videos - self.num_rows*self.num_rows
        else:
            self.num_rows = int(math.sqrt(num_good_videos / 2))
            cols = self.num_rows * 2
            remainder = num_good_videos - 2*self.num_rows*self.num_rows
        # setup basic row records
        self.rows = []
        for i in range(self.num_rows):
            row = { "cols": cols }
            self.rows.append(row)
        # try for an appoximation to a "nice" arrangement
        while remainder > 0:
            for i in range(self.num_rows):
                # extend odd rows first
                if i % 2 != 0 and remainder > 0:
                    self.rows[i]["cols"] += 1
                    remainder -= 1
            for i in range(self.num_rows):
                # extend even rows next
                if i % 2 == 0 and remainder > 0:
                    self.rows[i]["cols"] += 1
                    remainder -= 1
        if remainder > 0:
            log("OOPS, NON ZERO REMAINDER, SOMETHING BAD HAPPENED PLANNING THE GRID")
            quit()
        for i in range(self.num_rows):
            row = self.rows[i]
            cols = row["cols"]
            row["grid_w"] = int(output_w / cols)
            row["grid_h"] = int(output_h / self.num_rows)
            row["cell_w"] = (self.output_w - self.border*(cols+1)) / cols
            row["cell_h"] = (self.output_h - self.border*(self.num_rows+1)) / self.num_rows
            cell_aspect = row["cell_w"] / row["cell_h"]
            print("row:", i, "grid size:", row["grid_w"], "x", row["grid_h"])
            # print("  cell size:", self.cell_w, "x", self.cell_h, "aspect:", cell_aspect)

        log("video grid layout:")
        for row in self.rows:
            s = ""
            for col in range(row["cols"]):
                s += "x "
            log(" ", s)

    def update(self, videos, output_time):
        # compute placement/size for each frame (static grid strategy)
        row = 0
        col = 0
        if self.odd_offset >= 0:
            self.odd_offset = 0
        if self.even_offset < self.output_w:
            self.even_offset = self.output_w
        max_step = self.output_w * 0.010
        if self.num_rows >= 2:
            animated_start = True
        else:
            animated_start = False
        #num_good_videos = sum(v.reader is not None for v in videos)
        #print("good:", num_good_videos)
        sorted_vids = sorted(videos, key=lambda x: x.sort_order)
        #print("sorted:", len(sorted_vids))
        for v in sorted_vids:
            if v.reader is None:
                continue
            #print(row, col)
            row_info = self.rows[row]
            cols = row_info["cols"]
            cell_w = row_info["cell_w"]
            cell_h = row_info["cell_h"]
            if v.raw_frame is not None:
                frame = v.raw_frame
                # target grid location
                x = self.border + col * (cell_w + self.border)
                y = self.border + row * (cell_h + self.border)
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
                            self.even_offset += (cell_w + self.border)
                        else:
                            self.odd_offset -= cell_w
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
                v.size_w = cell_w
                v.size_h = cell_h
                col += 1
                if col >= cols:
                    col = 0
                    row += 1

        # outside videos loop!
        self.odd_offset += max_step
        self.even_offset -= max_step
