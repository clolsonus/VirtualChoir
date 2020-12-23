---
layout: post
title: Baseline Noise Cleanups (and Reverb)
categories: tech
---

## Noise profiling and reduction

Another feature I am excited to introduce is the ability to
automatically do baseline noise cleanup.  The system is already
finding the regions of each track that are music versus not music, so
the not-music regions can be glommed together and analyzed to create a
baseline noise profile.  This profile can then be removed (actually
reduced) from the original sample.  So things like hisses and buzzes
and hummmmms can largely go away.

There are trade-offs in audio quality though.  The more aggressive we
reduce noise, the more it does affect the original audio, so this
feature is currently used medium-lightly.

The system is using sox (an open-source audio swiss army knife) on the
back end to create the noise profile and do the noise reduction.

## Reverb

Now that we have sox connected into the system, we can leverage other
effects, in this case reverb.  Less is more, but a little in the right
place can help make the sound a bit bigger and nicer.

The specific mechanics is that very light noise reduction is applied
to all tracks on the top level folder, and now moderate reverb is
added to all these tracks as well.

Ideally projects are now organized with common parts grouped in
subfolders.  At the subfolder level slight more medium nose reduction
is applied and no reverb.
