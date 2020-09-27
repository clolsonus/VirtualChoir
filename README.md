# Experiments with Virtual Choirs

Virtual choirs have long fascinated me.  They can be a fun and
creative way to share talent and hard work.  In the age of world
pandemics when performance groups struggle to meet in person, and
often are unable to perform to a full audience, virtual choirs (or
orchestras) take on a new level of importance.

Even though technology is only a small part of a virtual performance,
it is a necessary hurdle to overcome.  The goal of this project is to
make those hurdles smaller and less expensive for groups just starting
out.

![demo choir](images/combined.png?raw=true "Combined Demo")

## How does this work?

* Create/record a reference track for your piece.
* Send this track to all participants with their part(s)
* Participants listen to the reference track through headphones, and
  then record themselves playing their part in sync with the reference
  track.
* Participants could possibly perform in small subgroups if they found a way to
  split/share headphones so they all simultaneously were listening to
  the same reference track.
* Copy all the recorded performances to a common folder on your computer.
* The tools here will scan all the clips in a folder, find their exact
  sync offsets (using math and engineering techniques), do a high
  quality mix of the audio together (more math), and render out the
  video clips in a gridded format -- all automatically.
* There is no need for expensive software tools or high end computers.
  These scripts do all the heavy lifting for you.
* At some point when you want a result with more creative and fancy
  editing, then you can explore the more professional tools.  But
  hopefully the tools here can get many groups started down the path
  with some positive quick results.

## Syncing clips

When using traditional video editing tools, the individual tracks are
dropped into a time-line and then manual slid and nudged in time to
align them.  This can be a fiddly process, but turns out to not be too
bad once you learn the tools and tricks.  This software does all of
that automatically for you, but one size doesn't fit all and the
nature of the piece can dictate the best approach.  This software has
3 approaches that can be used:

1. Use an initial clap (any sharp sound will do) to find the sync.
   Here the reference track would have a clap before the piece starts,
   and all the performers would clap at just the right time to sync
   the music.
2. For pieces that contain distinct beats and sharp notes, the
   software can find all the note onsets and use those across the
   entire piece to sync clips.
3. For pieces with less distinct note onsets (choral pieces, etc.) an
   intensity map can be created and used to sync the clips.
4. Beat syncing: an experimental feature is the ability to find the
   beats in tracks that are nearly the same place in other tracks and
   then move those notes slightly forward/back in time so they line
   up.  For percussive instruments where small errors in timing can be
   really noticeable, this can help clean that up at the expense of a
   bit of audio quality loss.
5. If none of these work for your piece, we can try new ideas, or
   allow for some manual tuning.

## Mixing audio

Once the synchronization offset of each clip is computed, the software
can mix all the clips together.  In physics, waves add to each other
when they are combined: in water two medium waves can make a big wave
at the moment the cross each other; this is also how we make
noise-canceling headphones.  So to get a really clean, pure mix of
all the tracks, the software simply adds the numerical representation
of all the waves together and divides by the total number of clips.

In addition, the mixer can convert mono clips to stereo and pan them
left or right to fill up the room so to speak.  It can also nudge the
clips (randomly) a tiny bit forward/back in time relative to each
other to give a more natural feel (not too perfect) to the group
performance.

## Mixing video

Video tracks are optional and can be recorded at the same time as the
audio in the same clip, or they can be recorded separately with the
performer lip syncing.

By default the software will find and sync any video clips in the
project folder and draw them out in a grid pattern.  The default
strategy is not exciting or creative, but it is a solid and clean
approach that can be done automatically with no additional software or
expertise.

Hopefully this is an acceptable trade off for people starting to learn
the process and navigate through the technology maze!  The more you
learn and the deeper you dive, the more of your own creativity you can
bring to the final result.

![chroma sync](images/chroma.png?raw=true "Chroma Representation")

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
and better; and if your performances can bring a smile to someone's
face, then it's all worth while!