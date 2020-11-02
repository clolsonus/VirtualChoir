---
layout: page
title: Next Steps
permalink: /next/
---

Making a virtual choir video really can be as easy as uploading your
movies to a google drive shared folder, filling out the request form
on the front page, and waiting for the result to be emailed back to
you.  But this is technology and sometimes things go sideways.  This
page outlines a few scenarios and how you can fix them.

# One or more of my tracks did not sync.

There is a really simple way to fix sync issues manually.  Hopefully
90% of your tracks synced ok and you only need to fix a few of them.

1. You will notice that your results include a file called
   "audacity_import.lof". This is a list of all your tracks and the
   computed time offset.
2. Copy this file to your project folder.
3. Launch audacity (this is a free/open-source program).
4. Import the "audacty_import.lof" file.  This will automatically
   bring in all your tracks at their computed offsets.
5. Use the audacity "Time Shift Tool" which has an icon that looks
   like this: <-> to fix any misplaced tracks.
6. Save as a new audacity project.  This will create a .aup file (with
   whatever name you chose for your project.)
7. Copy just the .aup file to your google drive shared folder.
8. Resubmit your request using the form on the front page.

When you run the job a second time, the system will find the .aup file
in your folder and read all the time offsets out of there.

# I need to change the audio level of one of my tracks.

Yes, maybe your piano accompaniment is too soft, or a voice comes out
too loud.  You can create a file called "hints.txt" to help the
automated system.  The format is simple, one track per line.  List the
track name in double quotes, followed by the hint.  For example:
```
"John.mp4" gain 0.5
"Jane.mp4" gain 1.1
```
Copy the hints.txt file to your shared folder and resubmit your request.

# One of my videos is rotated sideways.

This happens.  Every once in a great while, someone's phone just gets
confused about which way is up.  You can fix this with the hints.txt
file as well.  Rememnber, put the track file name in double quotes,
one track (and one hint) per line.  For example:
```
"John.mp4" rotate 180
"Jane.mp4" rotate 90
```
Valid rotations are 90, 180, and 270 in the clockwise direction.

# The automatic video grid system is great, but I need the videos laid out in a different order.

The gridded video system draws the tracks in alphabetical order.  So
you can go back and adjust the names of your tracks.  For example:
Jane.mp4 will be placed before John.mp4.  You can rename them "a
John.mp4" and "b Jane.mp4" to change the order.  If you have a larger
project and arrange the tracks in subfolders by part, you can name
your folders "a Soprano", "b Alto", "c Tenor", "d Bass".  Also keep in
mind that 10 is sorted alphabetically ahead of 2, so if you use a
numbering scheme, 01, 02, ..., 10, 11, ... will do what you expect.

# I need a title page and a credits page on my video, please!

No problem.  Using your favorite software create your title page and
credits page as an image.  You can even use power point (or google
slides) to make your pages and export them as an image.  Name them
"title.png" and "credits.png" (jpg is fine too) and copy these to your
shared project folder.  Submit the request again and these will be
added to your final video.

# I plan to do all the audio and video engineering myself, do you have a plugin for my DAW software to automatically align the tracks and save me a boatload of time?

Not exactly, but yes we can help. This system has an option to
generate new copies of all your individual audio tracks that are
padded/trimmed so they are all aligned at the exact same start time.
You can import these audio tracks into your favorite software package,
line them all up at zero and you are good to go.  Now you can focus
your time and talents on all the creative parts and skip some of the
super tedious parts.  Just look for the check box on the request form.

