# RPi Telecine Common functions
#
# Common functions shared by the telecine scripts 
# Provides for reading and writing the job's ini file
# Moving the film frame-by-frame
# Displaying a preview window
# Stopwatch class for benchmarking
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

import os
import time
import ConfigParser
import numpy as np
import cv2

import telecineControl
import telecineCamera as cam
import telecinePerforation


pf = telecinePerforation.telecinePerforation()
tc =  telecineControl.tcControl()


class telecineConfig():
    
    config = ConfigParser.SafeConfigParser()
    film_type = 'super8'

    shutter_speed = 0
    awb_gains = [1.5,1.5]
    show_gray = False
    brackets = False
    
    # Dynamic Range Compression
    #drc_values = sorted(cam.cam.DRC_STRENGTHS,key=cam.cam.DRC_STRENGTHS.get)
    drc_values = ('off','low','medium','high')
    drc = 'off'
    # Image Effects - allow a subset of ones known to work with the perf detection
    image_effect_values = ('none','denoise','colorbalance','saturation','washedout',
        'blur','film',  'colorswap','sketch','oilpaint','hatch','pastel','watercolor',\
        'posterise','colorpoint','cartoon')
    image_effect = 'none'
    
    perf_size = [0,0] # Perforation size - w,h
    perf_cx = 0 # Perforation centre line - cx

    # Crop offset size
    crop_offset = [0,0] # Cropping position relative to perf_centre - x_offset, y_offset
    crop_size = [0,0] # Size of crop in pixels - w,h
    ave_steps_fd = 0
    ave_steps_bk = 0
    pixels_per_step = 5

    def __init__(self):
	pass
	 
    def read_configfile(self,job_name):
	if job_name != '':
	    self.job_name = job_name
	    self.configname = job_name + '.ini'
	# Read job config file - so we retain existing settings
	# Get baseline exposure from ~/.telecine.ini
	cnf_file = self.config.read([os.path.expanduser('~/.telecine.ini'),self.configname])
	section = 'Telecine'
	if section not in self.config.sections():
	    self.config.add_section(section)

	options = self.config.options(section)
	if 'film_type' in options:
	    self.film_type = self.config.get(section,'film_type')
	if 'shutter_speed' in options:
	    # Use a previously recorded shutter speed as a baseline
	    self.shutter_speed = self.config.getint(section,'shutter_speed')
	else:
	    self.shutter_speed = 2000
	if 'gain_r' in options:
	    self.awb_gains[0] = self.config.getfloat(section,'gain_r')
	if 'gain_b' in options:
	    self.awb_gains[1] = self.config.getfloat(section,'gain_b')
	if 'perf_w' in options:
	    self.perf_size[0] = self.config.getint(section, 'perf_w')
	if 'perf_h' in options:
	    self.perf_size[1] = self.config.getint(section, 'perf_h')
	if 'perf_cx' in options:
	    self.perf_cx = self.config.getint(section, 'perf_cx')
	if 'crop_offset_x' in options:
	    self.crop_offset[0] = self.config.getint(section, 'crop_offset_x')
	if 'crop_offset_y' in options:
	    self.crop_offset[1] = self.config.getint(section, 'crop_offset_y')
	if 'crop_w' in options:
	    self.crop_size[0] = self.config.getint(section, 'crop_w')
	if 'crop_h' in options:
	    self.crop_size[1] = self.config.getint(section, 'crop_h')
	if 'brackets' in options:
	    self.brackets = self.config.getboolean(section, 'brackets')
	if 'grayscale' in options:
	    self.show_gray = self.config.getboolean(section, 'grayscale')
	if 'ave_steps_fd' in options:
	    self.ave_steps_fd = self.config.getint(section, 'ave_steps_fd')
	else:
	    self.ave_steps_fd = 300
	if 'ave_steps_bk' in options:
	    self.ave_steps_bk = self.config.getint(section, 'ave_steps_bk')
	else:
	    self.ave_steps_bk = 300
	if 'pixels_per_step' in options:
	    self.pixels_per_step = self.config.getfloat(section, 'pixels_per_step')
	else:
	    self.pixels_per_step = 4.0
	


    def write_configfile(self):
	# Write job config file
	with open(self.configname,'w') as f:
	    self.config.set('Telecine','job_name',self.job_name)
	    self.config.set('Telecine','film_type',self.film_type)
	    self.config.set('Telecine','shutter_speed',str(self.shutter_speed))
	    self.config.set('Telecine','gain_r','%.3f'%(self.awb_gains[0]))
	    self.config.set('Telecine','gain_b','%.3f'%(self.awb_gains[1]))
	    self.config.set('Telecine','brackets',str(self.brackets))
	    self.config.set('Telecine','grayscale',str(self.show_gray))
	    if self.perf_size != (0,0):
		self.config.set('Telecine','perf_w','%d'%self.perf_size[0])
		self.config.set('Telecine','perf_h','%d'%self.perf_size[1])
		self.config.set('Telecine','perf_cx','%d'%self.perf_cx)
		self.config.set('Telecine','crop_w','%d'%self.crop_size[0])
		self.config.set('Telecine','crop_h','%d'%self.crop_size[1])
		self.config.set('Telecine','crop_offset_x','%d'%self.crop_offset[0])
		self.config.set('Telecine','crop_offset_y','%d'%self.crop_offset[1])
	    self.config.set('Telecine','ave_steps_fd',str(self.ave_steps_fd))
	    self.config.set('Telecine','ave_steps_bk',str(self.ave_steps_bk))
	    self.config.set('Telecine','pixels_per_step','%.3f'%(self.pixels_per_step))
	    
	    self.config.write(f)
	
cnf = telecineConfig()
	
# Some useful values returned by cv2.waitKey - 
# probably platform dependent
# These work on the Pi
cv2_keys = {'RightArrow':65363, 'LeftArrow':65361, \
			'UpArrow':65362, 'DownArrow':65364, \
			'Escape':27, 'Enter':10, \
			'Home':65360, 'End':65367, \
			'PgUp':65365, 'PgDn':65366, 'Tab':9 } 

# Utility function to constrain values
constrain = lambda n, minn, maxn: max(min(maxn, n), minn)

def display_shadow_text(img,x,y,text):
    """
    Displays with a grey shadow at point x,y
    """
    text_color = (255,255,255) #color as (B,G,R)
    text_shadow = (0,0,0)
    text_pos = (x,y)
    shadow_pos = (x+1,y+1)
    cv2.putText(img, text, shadow_pos, cv2.FONT_HERSHEY_PLAIN, 1.25, text_shadow, thickness=1, lineType=cv2.CV_AA)
    cv2.putText(img, text, text_pos, cv2.FONT_HERSHEY_PLAIN, 1.25, text_color, thickness=1, lineType=cv2.CV_AA)
    return img

def display_image(window_name,img,reduction=2, text=''):
    """ 
    Resize image and display using imshow. Mainly for debugging 
    Resizing the image allows us to see the full frame on the monitor
    as cv2.imshow only allows zooming in.
    The reduction factor can be specified, but defaults to half size
    Text can also be displayed - in white at top of frame
    """
    reduction = constrain(reduction,1.2,6)
    newx,newy = int(img.shape[1]/reduction),int(img.shape[0]/reduction)  #new size (w,h)
    newimg = cv2.resize(img,(newx,newy))
    if text != '':
	display_shadow_text(newimg,20,25,text)
    cv2.imshow(window_name,newimg)
    
def display_thumb(window_name,img,reduction=2, text=''):
    """ 
    Displays a reduced sized image - but use Numpy strides to do the resize.
    A lot faster than using cv2.resize, but is limited to integer reduction factors
    no interpolation is done, so is subject to aliasing. If no text is needed, no
    copy of the image data is done.
    """
    reduction = int(constrain(reduction,2,6))
    if text == '':
	# Fast - doesn't copy the image data
	newimg = img[::reduction,::reduction]
    else:
	# Putting text only works on a copy of the image
	newimg = img[::reduction,::reduction].copy()
	display_shadow_text(newimg,20,25,text)

    cv2.imshow(window_name,newimg)

def next_frame():
    # Move to next frame
    steps = cnf.ave_steps_fd
    if pf.found:
	diff = pf.yDiff # Pixels of centre of perf to centre of ROI
	steps = steps + int(round(diff/cnf.pixels_per_step))
    print('Moving %d steps'%(steps))
    tc.steps_forward(steps)
    
    
def prev_frame():
    # Move to next frame
    steps = cnf.ave_steps_bk
    if pf.found:
	diff = pf.yDiff # Pixels of centre of perf to centre of ROI
	steps = steps - int(round(diff/cnf.pixels_per_step))
    print('Moving %d steps'%(steps))
    tc.steps_back(steps)
    

def centre_frame():
    # Attempt to centre the frame on the perforation
    done = False
    count = 10
    print('Centering')
    while (count > 0) and not done:
	count -= 1
	img = cam.take_picture()
	pf.find(img)
	if pf.found:
	    if pf.yDiff > 10:
		tc.steps_forward(int(pf.yDiff/cnf.pixels_per_step))
	    elif pf.yDiff < -10:
		tc.steps_back(int(abs(pf.yDiff)/cnf.pixels_per_step))
	    else:
		# Pretty close to the centre
		done = True
	else:
	    # No perforation found so step forward 1/3 frame which should
	    # get a perforation into the ROI
	    tc.steps_forward(int(cnf.ave_steps_fd/3))

def fast_wind(frames,d=True):
    # Fast wind a lot of frames
    steps = cnf.ave_steps_fd if d else cnf.ave_steps_bk
    steps = steps * frames
    tc.steps_forward(steps) if d else tc.steps_back(steps)
    centre_frame()
    
def sanitise_job_name(job_name):
    # Sanitise the jobname as we'll be creating a folder from it
    delchars = ''.join(c for c in map(chr, range(256)) if not c.isalnum())
    job_name = job_name.translate(None, delchars)
    
    if not job_name:
	print('Job name needs to consist of characters "azAZ-_"')
	quit()
	
    return job_name
    
class Stopwatch():
    """
    Simple timing class used to record time of capturing frames
    """
    
    def __init__(self):
	self.start_time = None
	
    def start(self):
	if self.start_time is not None:
	    # Already started 
	    return
	self.running = True
	self.start_time = time.time()
	
    def stop(self):
	# Stop and return elapsed time
	t = time.time()-self.start_time
	self.start_time = None
	return t