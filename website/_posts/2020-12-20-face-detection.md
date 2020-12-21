---
layout: post
title: Face Detection and Following
categories: tech
---

I'm excited to introduce a newly added feature: face detection and
tracking.

Before the gridded video is drawn for the first time, the system scans
through each input video track and locates the faces at 100 equally
spaced intervals and saves this information.

When the gridded video is being rendered, the face location in each
frame of each track is smoothly interpolated.  The system will
automatically crop, pan, scale each face to best fit in the available
grid space.  In addition, sub-pixel cropping is used on the original
input video to make very slow panning/zooming smoother.

The goal is to see the performers better, use screen space more
efficiently, and not create any noticable distractions in the proces.