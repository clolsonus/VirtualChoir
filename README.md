# Virtual Choir Syncing, Mixing, and Rendering Tools

Virtual choirs allow people from across the world or just across town
to collaborate and make music together.  If you are an experienced
creator, these tools can help your project come together more quickly.
For those that are new, these tools can open the door to this
fascinating world (without requiring audio or video editing experience
or expensive software) so that you and your performers can show off
your efforts and talents!

[![Natus est Nobis](http://img.youtube.com/vi/Z_pOPgHhDyI/0.jpg)](https://www.youtube.com/watch?v=Z_pOPgHhDyI "Natus est Nobis (demo of software)")

## Basic workflow

* Record a reference track for your piece.
* Send this track to all participants with their part(s).
* Participants listen to the reference track through headphones, and
  then record themselves playing their part in sync with the reference
  track.
* Collect all the preformance tracks in a folder.
* The tools here will scan all the audio and video tracks in your
  project, then analyze and compare every track to every other track
  to find a best mutual syncronization (using math, frequencies,
  correlations, optimizations ... engineering stuff.)
* Next your audio tracks will get mixed together.
* Finally all your videos will be rendered in a simple gridded fashion
  to produce a virtual choir perfomance.

### Sometimes a few tracks won't sycronize properly, what then?

* In the first pass, these tools write out an audacity import file
  that lists all your tracks with the computed time offset.  You can
  open audacity, import all the individual tracks (at the proper time
  offsets) and investigate which track(s) didn't sync, and manually
  adjust them.  When it's just a track or two, this is really easy and
  quick.  When you are happy with the manual adjustments, save your
  audacity project as a .aup file.  You can sync videos this way too,
  by syncing their audio tracks in audacity (if they aren't already
  synced automatically in the first pass.)
* Run the program a 2nd time, but now we see the .aup file and read
  the time offsets out of that.  Then the tracks are mixed and the
  gridded video is automatically rendered as before.

### What if I need to rotate a video, or boost the level of a piano
    accompianment, or mute a voice that isn't working out?

* All this is possible by creating a 'hints.txt' file.  Just list a
  file name along with the video rotation hint or audio gain hint, and
  rerun the program.

### What if I want to do a fancy video edit and do a lot of extra
    fixup work on the audio?

* We can write all the audio tracks back out with padding/trimming so
  they all align exactly at time zero.  This lets you import all your
  tracks into your favorite DAW (digital audio workstation) software,
  but saves you the time of manually fixing the time syncronization
  for every track.

## Syncing tracks

There are two sync strategies available.

1. The wave samples of each track are correlated with every other
   track to find a best fit.  The time offsets for all tracks relative
   to all the other tracks are compared against each other to produce
   a mutually optimal final sync.  (The softwareis solving a big
   optimization problem to find the best mutual fit.)

2. Use an initial clap (or 4 claps) to mark the sync.  The software
   searches the lead in time before the first clear notes for sharp
   claps and performs a best fit alignment of all the tracks using
   those clap(s).

3. As described above, audacity can be used to override or fix or fine
   tune any sync issues that the automatic system was unable to
   resolve properly.

## Mixing audio

The software has a built in high precision audio mixer.  Gains can be
specified for any individual track.  For example, piano accompianment
of a choir can be made louder to balance out a 50 voice choir.  A
specific instrument (i.e. trumpet) could be softened so it doesn't
dominate a piece. If a participant just isn't working out (which might
happen in a kids choir for example) you can still include their video,
but mute the audio and no one will know.

## Mixing video

Video tracks are optional and can be recorded at the same time as the
audio in the same clip, or they can be recorded separately with the
performer lip syncing.

By default the software will find and sync any video clips in the
project folder (sync based on the audio track)and draw them out in a
grid pattern.  The default strategy is not exciting or creative, but
it is a solid and clean approach that can be done automatically with
no additional software or expertise.

These tools can handle a wide variety of video formats, frames per
second, aspect ratios, etc. and still grid and draw them all out
properly in sync.

![chroma sync](images/chroma.png?raw=true "Chroma Representation")

## Use Case Ideas

* Choir practice!  This may not be your final performance, but you can
  still have participants submit their tracks and quickly mix them
  together so you can provide feedback and show progress.
* Some people know their band would sound a lot better if they played
  all the instruments.  Now's your chance!
* Just uses these tools to create time aligned versions of your tracks
  and import those into your favorite fancy audio/video editor tools
  and save a ton of time.
* What other ideas do you have?

# Installation

For now, these scripts require ffmpeg, and a python distribution to
already be found on your system.  If you don't have python already,
you may find 'anaconda' a nice option.  Make sure you install python
version 3 (not version 2.)

These scripts depend on a few libraries that are not normally found in
a standard python distribution.  These extra libraries can easily be
installed with "pip".  For those with opinions about how to manage
python dependencies, maybe your linux distribution already has some of
these libraries packaged, or maybe your python system (i.e. conda) has
some of these available already.  It may be worth checking both of
those first and then using pip if no prepackaged libraries are found.

When I do this sort of thing, I run the script, see what package
import fails, install it, repeat ..., eventually I have all the
dependencies and the script works, yeah!

# Questions:

I'm sure you have many.  Please feel free to ask for help!  As I write
this, these software tools are very young and not tested across a wide
set of performances.  I am new to this technology too, and learning as
I go.  So let's learn together; help me make these tools work easier
and better.

If your performances can bring a smile to someone's face, then it's
all worth while!

# Resources:

## Other software, tools, and ideas for creating virutal works:

  https://docs.google.com/document/d/1QK-PVHsBMGDT5RCx258rMFw1Aww4yGV8YkmHjXPrrsc/edit?usp=sharing

## Sample recording instructions:

   https://docs.google.com/document/d/1mWFmZ76PZErq-XEIeCNmw1FZdtWXVHjOARTSdNITCzA/edit?usp=sharing

