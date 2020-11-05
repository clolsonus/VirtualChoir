---
layout: page
title: About
permalink: /about/
---

# About: Virtual Choir Maker

Virtual Choir Maker uses math, engineering, and computer algorithms to
syncrohonize your tracks, mix them together, draw a gridded video, and
send you the result.

You only need to worry about carefully recording your tracks in sync
with a reference track.  All the track syncronization, audio
engineering, and video editing is done by the automated tools.  You
don't need extra software, you don't need video editing skills, you
don't need a monster PC to crunch everything.

Under the hood, many of the audio processing functions are handled by
librosa and pydub.  Video and audio reading/writing is handled
by ffmpeg.  Gridded video rendering is done with opencv.  The code is
written in python.  It is open-source, you can go take a look at it,
and even run the tools on your own computer.  You can find the Virtual
Choir Maker source code on
[github](https://github.com/clolsonus/VirtualChoir).

# About: the Author

Virtual Choir Maker is written by Curtis Olson.  Curt has a full time
day job a the University of Minnesota, Aerospace Engineering
Department, Unmanned Aerial Systems Lab.  There he is chief test pilot
and contributes to a variety of research and student projects.  Curt's
degree is in Computer Science if you were wondering why an aerospace
engineering is writing python code to automate virtual choir
construction.  Oh, and actually quite a few concepts developed or
learned at Curt's day job show up here in this project!

# About: the Automated Cloud Tools

As I write this, the cloud system that processes your requests is
literally a linux server in Curt's basement.  The system is able to
sync your tracks from a google shared folder if you have made the
folder visable (read-only with the link.)  Your results are shared
back with you using [Filemail](filemail.com) and will be available for
7 days.

# Thanks!

There is no way to keep a full list of everyone to thank, but for
their invaluable help getting this project rolling, providing ideas,
and samples to test with, many many thanks to:

* Kathleen Hansen - Master Director, San Diego Chorus
* Clement Cano - Vocal Arts Director, Sacred Heart Schools, Atherton CA