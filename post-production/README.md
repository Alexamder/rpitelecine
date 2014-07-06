# Post-production

These are some simple scripts and snippets of code designed to be run on a full 
power PC, as the Raspberry Pi's ARM processor really isn't up to the job of 
transcoding and processing the large number of images into video. 

My PC runs OpenSUSE Linux with an i5 Processor, and some of the routines take a 
long time.

There are lots of potential processing options, using Linux, OSX or Windows. 
On Linux Openshot and Kdenlive are very good video editors.

## Getting the images onto the PC

Copy the files to from the Pi to the PC. 50 feet of film generates about 5-6GB 
of png files, so it's probably quicker to shut down the Pi, remove the SD card, and
copy the files using an SD card reader on the host PC.  If time isn't an issue, or
you want to keep the Pi running, it's possible to use scp to copy the files over.
As the pictures are stored on the SD card which uses the Ext4 filesystem, you won't be
able to read the card directly on a Windows system without loading additional software.

## Copy files using scp

From the PC, in a terminal:  

```
mkdir <jobname>
cd <jobname>
scp pi@<IP address of Pi>:/home/pi/rpitelecine/<jobname>/*png
```

Replace the job name with the one you chose, and the IP address of the Pi on your 
network. This of course assumes you have set up the ssh server on your Pi. It is possible
to get a work-in-progress copy while the telecine is running a job, but while the
copy is running, the speed of the telecine job halves.

The scp line would be something like:

```
scp pi@192.168.0.13:/home/pi/rpitelecine/familyfilm1/*png
```

With the Pi set up wirelessly, each image takes a second or so to copy. It is quicker to copy 
from the SD card directly, if you are running Linux on the PC. Bear in
mind you are copying about 3,500 pictures for a 50 foot reel of film.

## Create an MP4 film of the video using mencoder

A quick and dirty way of getting video from all the pictures is to use mencoder on
the command line. It's part of mplayer, and should be installed when you installed that
program. I have successfully used this command line:

```
mencoder -nosound -ovc lavc -lavcopts vcodec=mpeg4:mbd=2:trell:autoaspect:vqscale=3 -vf scale=1024:768 -mf type=png:fps=18 mf://img*.png -o <name>.avi
```

Replace <name> at the end with the name of the video you want to create.
You may also want to adjust the framerate after the =fps option - for Super 8 film it
should be 18 frames per second, for standard 8mm it should be 16. Though you may need to 
adjust. Super 8mm with sound is likely to have been shot at 24fps, and older film may be
shot at slower than 16fps...

Digital video players I have tried on the PC, media player hardware, and youtube doesn't 
seem to have trouble with the odd framerate, so it isn't necessary to interpolate frames, 
or alter the rate unless you wish to output to a media like DVD with a fixed 25fps format.

# Use enfuse for combining bracketed pictures

Enfuse is part of Hugin - and is a command line utility that can combine two or more
pictures of the same scene taken with different exposures. [Details here](http://enblend.sourceforge.net/)

Film has a wider dynamic range than is available with the Raspberry Pi camera, so in 
some circumstances it is useful to take two (or possibly more) picturs of the film frame
in order to get as much detail out of it as possible - this is especially true with underexposed
film, or in scenes with a lot of shadow. Some scenes benefit more than others with this
processing, so it may be better to process the normal exmposures as well, and combine
the best scenes using a video editor.

Enfuse can be used to simply combine bracketed sequences pictures using this Python script:

```python
import glob
import os
import subprocess

brackets = 2
name_template = 'img-?????-?'
fmt = '.png'
out_prefix = 'frame-'

files=sorted(glob.glob(name_template + fmt))
n_frames =  len(files)/brackets
FNULL = open(os.devnull, 'w')

processes = 4	# Optimise for number of cores - 4 works well on my i5
counter = 0
while files:
    frame1 = files.pop(0)
    frame2 = files.pop(0)
    outfile = out_prefix + frame1[4:9] + fmt
    print('{}+{} -> {}'.format(frame1,frame2,outfile))
    counter += 1
    cmd = ['enfuse', '-v0', frame1, frame2, '-o', outfile ]
    if counter % processes == 0:
        # Wait until this one finishes
        subprocess.call( cmd, stdout=FNULL, stderr=subprocess.STDOUT)
    else:
        # run in background
        subprocess.Popen( cmd, stdout=FNULL, stderr=subprocess.STDOUT )
```
It very simply goes through all the frames in a sequence, and combines pairs with matching
sequence numbers, creating a new sequence. Enfuse runs slowly, about 1 a second even on my 
Core i5 - but as it only uses a single core on the processor, this script backgrounds 3 of every four, so in
effect running four times faster than simply doing one at a time.