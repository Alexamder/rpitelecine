"""
A small script to combine the paired exposures taken with the
Raspberry Pi based telecine in bracket mode. 
Run it from the folder with the exposures in. 
The script assumes that all filenames will be in the format:
img-?????-?.png - with the first block of ?s denoting the frame
number and the last one the subframe.
This scipt also assumes that the images come in pairs only.
To speed things up three of every four calls to enfuse are backgrounded
to make use of available cores on the PC, otherwise only one core is used,
and each enfuse takes about 1 second. I tried compiling enfuse/enblend to make
use of the multiprocessing feature, but it crashes on my openSuse system.
"""

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
        