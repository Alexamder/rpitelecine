#!/usr/bin/env python
#
# RPi Telecine - Run the telecine job
#
# Usage: python tc-run job_name -s|--start [start_frame] -e|--end[end_frame] 
#
# Command line options:
# -s, --start   	Start frame counter
# -e, --end     	End counter
# -j, --jpeg    	Save jpegs instead of PNG
# -r, --reverse		Run transport backwards
# -b, --brackets        Bracket exposure
#
# Writing the images is done in a concurrent thread to the picture taking and
# film transport. 
#
# This script runs in command line only, so can be run in a Screen session, allowing
# it to run autonomously.
#
# Copyright (c) 2014, Jason Lane
# 
# Redistribution and use in source and binary forms, with or without modification, 
# are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this 
# list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice, 
# this list of conditions and the following disclaimer in the documentation and/or 
# other materials provided with the distribution.
# 
# 3. Neither the name of the copyright holder nor the names of its contributors 
# may be used to endorse or promote products derived from this software without 
# specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR 
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES 
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; 
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON 
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT 
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS 
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from __future__ import division

import subprocess
import argparse
import os
import ConfigParser
import time
import threading
import Queue
import cv2
import numpy as np

from telecineCommon import *

import telecineControl
import telecineCamera as cam
import telecinePerforation

job_name = ''
start_frame = 0
end_frame = 0
frames_count = 0
current_frame = 0
capture_direction = 1
capture_ext = 'png'
config = ConfigParser.SafeConfigParser()

def parse_commandline():
    # Command line arguments
    global job_name, start_frame, end_frame, frames_count
    global current_frame, capture_direction, capture_ext, reverse, brackets
    parser = argparse.ArgumentParser()
    parser.add_argument('jobname', help='Name of the telecine job')
    parser.add_argument('-s','--start', type=int, help='Start frame number')
    parser.add_argument('-e','--end', type=int, help='End frame number')
    parser.add_argument('-j','--jpeg', help='Save Jpeg images',	action='store_true')
    parser.add_argument('-r','--reverse', help='Run backwards', action='store_true')
    parser.add_argument('-b','--brackets', help='Bracket exposures', action='store_true')

    args = parser.parse_args()
    
    job_name = sanitise_job_name(args.jobname)

    start_frame = args.start if args.start else 0
    end_frame = args.end if args.end else 0
    frames_count = abs(end_frame - start_frame)+1
    if frames_count==0:
	print('Job needs to know how many frames')
	quit()
    capture_direction = 1 if end_frame > start_frame else -1
    current_frame = start_frame
    if args.jpeg:
	print('Saving as jpeg')
	capture_ext = 'jpg'
    brackets = args.brackets
    if args.brackets:
	print('Bracketing on')
    reverse = args.reverse
    if args.reverse:
	print('Reverse capture')

def make_crop():
    # Return a Numpy slice to crop the image around the perforation
    cx,cy = pf.centre
    crop_x = cx+cnf.crop_offset[0]
    crop_y = cy+cnf.crop_offset[1]
    return pf.crop_slice( (crop_x, crop_y, cnf.crop_size[0],cnf.crop_size[1]) )

q = Queue.Queue(5)
job_finished = False
still_writing = True

def writer():
    # Writer is run in a separate thread, so that writing is concurrent
    # to taking the pictures.
    global q, job_finished, still_writing
    write_time = Stopwatch()
    while not job_finished:
	still_writing = True
	while not q.empty():
	    write_time.start()
	    fn,img = q.get()
	    try:
		cv2.imwrite(fn,img)
		t=write_time.stop()
		print('Written {} in {:.02f} secs'.format(fn,t))
	    except:
		t=write_time.stop()
		print('Failed to write {} in {:.02f} secs'.format(fn,t))
    # Finished all jobs and queue is empty
    still_writing = False

failed_frames = 0

taking_time = Stopwatch()
taking_times = []

def single_picture(current_frame):
    # Takes one picture and sends it to the writer
    global cnf, capture_ext,fpath,failed_frames
    global taking_time, taking_times
    fname = 'img-{:05d}.{}'.format(current_frame,capture_ext)
    taking_time.start()
    img = cam.take_picture()
    t = taking_time.stop()
    taking_times.append(t)
    print('Taken {} in {:.2f} secs'.format(current_frame,t))
    if cnf.show_gray:
	img = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    #print('Img Shape: {}'.format(img.shape))
    found = pf.find(img)
    if not found:
	# Not found a perforation - but save full frame anyway
	# So we can manually crop it later - if we have a previous
	# perforation stored, then use this to fake a successful crop find
	# even though it may be misaligned - means we don't get a missing frame
	# when we're previewing
	print('Perforation failed:{}'.format(fname))
	failed_frames += 1
	failedname = 'failed-' + fname
	failedname = os.path.join( fpath, failedname )
	q.put( (failedname,img) )
	if pf.prev_position != (0,0):
	    # Use last successful crop as a basis 
	    found = True
    else:
	# Reset fail count if we found the perforation
	failed_frames = 0
    if found:
	img = img[make_crop()]
	fname = os.path.join(fpath,fname)
	q.put( (fname,img) )
    
def bracket_pictures(current_frame):
    # Takes the bracketed pictures
    # At present it is hard coded to take two exposures - one normal and
    # a much longer exposure.
    global cnf, capture_ext,fpath,failed_frames
    global taking_time, taking_times
    fnames = [ 'img-{:05d}-1.{}'.format(current_frame,capture_ext),\
	       'img-{:05d}-2.{}'.format(current_frame,capture_ext) ]
    taking_time.start()
    imgs = cam.take_bracket_pictures()
    t = taking_time.stop()
    taking_times.append(t)
    print('Taken {} in {:.2f} secs'.format(current_frame,t))
    if cnf.show_gray:
	imgs[0] = cv2.cvtColor(imgs[0],cv2.COLOR_BGR2GRAY)
	imgs[1] = cv2.cvtColor(imgs[1],cv2.COLOR_BGR2GRAY)
    found = pf.find(imgs[0])
    if not found:
	# Not found a perforation - but save full frame anyway
	# So we can manually crop it later - if we have a previous
	# perforation stored, then use this to fake a successful crop find
	# even though it may be misaligned - means we don't get a missing frame
	print('Perforation failed:{}'.format(fnames[0]))
	failed_frames += 1
	failednames = [ os.path.join( fpath, ('failed-' + fnames[0]) ), \
			os.path.join( fpath, ('failed-' + fnames[1]) ) ]
	q.put( (failednames[0],imgs[0]) )
	q.put( (failednames[1],imgs[1]) )
	if pf.prev_perforation:
	    # Use last successful crop as a basis 
	    pf.perforation = pf.prev_perforation
	    pf.cx = pf.perforation[0]+(pf.perforation[2]//2)
	    pf.cy = pf.perforation[1]+(pf.perforation[3]//2)
	    found = True
    else:
	# Reset fail count if we found the perforation
	failed_frames = 0
    if found:
	imgs[0] = imgs[0][make_crop()]
	imgs[1] = imgs[1][make_crop()]
	fnames = [ os.path.join(fpath,fnames[0]), os.path.join(fpath,fnames[1]) ]
	q.put( (fnames[0],imgs[0]) )
	q.put( (fnames[1],imgs[1]) )

def run_job():
    global q, job_finished
    global cnf,job_name, start_frame, end_frame 
    global capture_direction, capture_ext, fpath
    global brackets, reverse
    global pf, tc, cam
    global failed_frames
    
    max_fails = 5 # Maximum number of adjacent failed perforation detections
    
    job_time = Stopwatch()
    job_time.start()
    job_finished = False
    t = threading.Thread(target=writer)
    t.start()
    print('Film type: {}'.format(pf.film_type))
    try:
	tc.light_on()
	cam.setup_cam(cnf.awb_gains, cnf.shutter_speed)
	centre_frame()
	frame_time = Stopwatch()
	frame_times = []
	end_frame = end_frame + capture_direction	# Make list inclusive
	for current_frame in range(start_frame,end_frame,capture_direction):
	    frame_time.start() # Start timing
	    taking_time.start()
	    if not brackets:
		single_picture(current_frame)
	    else:
		bracket_pictures(current_frame)
	    if failed_frames >= max_fails:
		print('Maximum failed perforation detections')
		break
	    if not reverse:
		next_frame()
	    else:
		prev_frame()
	    t = frame_time.stop()
	    print('Frame {} in {:.2f} secs'.format(current_frame, t))
	    frame_times.append(t)
    finally:
	tc.light_off()
	cam.close_cam()
	job_finished = True	# Signals the writing thread to finish
	while still_writing:
	    # Wait until writing queue is empty
	    time.sleep(0.1)
    jt = job_time.stop()
    minutes = jt // 60
    seconds = jt % 60
    job_finished = True		
    ave_per_frame = sum(frame_times) / len(frame_times)
    ave_camera_time = sum(taking_times) / len(taking_times)
    # Some stats
    print('%d frames'%(len(frame_times)))
    print('Elapsed time {:.0f} mins {:.1f} secs'.format(minutes,seconds))
    print('Average time per frame: {:.2f} secs'.format(ave_per_frame))
    print('Fastest frame: {:.2f} secs'.format(min(frame_times)))
    print('Slowest frame: {:.2f} secs'.format(max(frame_times)))
    print('Average camera time per frame: {:.2f} secs'.format(ave_camera_time))
    print('Fastest frame: {:.2f} secs'.format(min(taking_times)))
    print('Slowest frame: {:.2f} secs'.format(max(taking_times)))
    
  
if __name__ == '__main__':
    parse_commandline()
    cnf.read_configfile(job_name)
    brackets = brackets or cnf.brackets
    pf.set_film_type(cnf.film_type)
    pf.set_size( cnf.perf_size )
    pf.cx = cnf.perf_cx
    pf.img_size = cam.cam.MAX_IMAGE_RESOLUTION
    try:
	pf.set_roi()
    except:
	print "Cannot set ROI - run setup and select a perforation"
	quit()

    print('Job:%s  %d-%d : %d frames'%(job_name,start_frame,end_frame,frames_count))
    print('Shutter speed: %d gain_r:%.3f gain_b:%.3f'%(cnf.shutter_speed,cnf.awb_gains[0],cnf.awb_gains[1]) )
    print('cx:{} Perf size:{}'.format(pf.cx,pf.size)) 
    print('Crop: %d:%d %dx%d'%(cnf.crop_offset[0],cnf.crop_offset[1],cnf.crop_size[0],cnf.crop_size[1]))
    if capture_direction > 0:
	print('Counting Forwards')
    else:
	print('Counting Backwards')
    
    # Create capture directory if it doesn't already exist
    fpath = os.path.join('.',job_name)
    if not os.path.exists(fpath):
	try:
	    os.mkdir(fpath)
	except:
	    print('Error creating capture directory: %s'%fpath)
	    quit()
    if not os.path.isdir(fpath):
	print('%s is a file not a directory'%fpath)
	quit()

    run_job()
    
    