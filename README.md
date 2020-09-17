# Experiments with Virtual Choirs

In the age of covid-19 when performance groups struggle to meet and
practice in person, and often are unable to perform to a full
audience, virtual choirs (or orchestras) are a fun thing to create.
However, the manual editing effort and technical skills required to
create the final videos can be daunting.  The goal of this project is
to develop some automated scripts so that smaller groups or
individuals can create their own virtual choir videos without needing
the immense technical skill and editing that these projects normally
require.

## Basic concept

* Step 1: create a reference track with a sync clap at the start.
  Ex. 1, 2, 3, 4, CLAP, 2, 3, 4, PLAY, 2, 3, 4 ...
* Send this track to all participants with their part(s)
* Participants listen to the reference track through headphones, clap
  at the exact same time as the reference clap, and then play along
  their part.  Participants record themselves playing with a phone or
  any movie camera.
* These scripts will load all the individual movie clips,
  automatically find the sync claps, sync all the audio streams, and
  mix them into a single virtual choir (or orchestra.)

## Here is what I have so far:

1. Scan for an initial 'sync' clap. (done!)
2. Trim the start of each clip the correct amount to perfectly align
  all the claps (done!)
3. Mix the audio tracks together (done!)

![chroma sync](images/chroma.png?raw=true "Chroma Representation")

## Here are fancier things I plan (hope) to add:

1. Beat syncing.  Find small adjustments throughout the piece to
   improve the sync.
2. Generate a choir video with an array of the input videos (with the
   fully mixed sound track.)
3. For larger choirs, enable a grouping function along with video
   mixing options to be able to zoom on groups or individuals to make the
   video more interesting.


# Installation

For now, these scripts require a python distribution to already be
found on your system.  If you don't have python already, you may find
'anaconda' a nice option.  Make sure you install python3 (not 2.)

These scripts depend on a few libraries that are not normally found in
a standard python distribution.  These extra libraries can easily be
installed with "pip".  For those with opinions about how to manage
python dependencies, maybe your linux distribution already has some of
these libraries packaged, or maybe your python system (i.e. conda) has
some of these available already.  It may be worth checking both of
those first and then using pip if no pre-packaged libraries are found.

When I do this sort of thing, I run the script, see what package
import fails, install it, repeat ..., eventually I have all the
dependencies and the script works, yeah!