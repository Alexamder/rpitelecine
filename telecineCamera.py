# RPi Telecine Camera Control
#
# Code to encapsulate the operation of the camera.
#	
# Basically this isolates the fixed settings we use during the
# taking process. Images returned are bgr format Numpy arrays
# that can be used by openCV.
#	
# Prerequisites:
# Uses Python-picamera by Dave Hughes from: 
# https://pypi.python.org/pypi/picamera/
# or use sudo apt-get install python-picamera on your Pi.
#	
# Uses array API of Picamera 1.5+ to return a Numpy array
#
# As of May 2014, it seems to be necessary to set the memory split
# in raspi-config to be 192M, otherwise we seem to get MMAL 
# out-of-memory errors.
#
# 
#	
# close_cam() should be called at the end of the program otherwise
# it could result in memory leaks in the GPU 
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
import picamera
import picamera.array 

# Use a stream for storing the captured image to save using the SD card
# for intermediate storage
cam = picamera.PiCamera()

def setup_cam(awb_gains,shutter,drc='off',effect='none'):
	""" 
	Camera settings for telecine
	Need fixed shutter speed, AWB etc for consistency 
	between frames. The awb_gains and shutter speed are established
	in the job tc-whitebalace.py
	"""
	cam.resolution = cam.MAX_IMAGE_RESOLUTION # 2592x1944
	cam.ISO=100
	cam.awb_gains=awb_gains
	cam.awb_mode='off'
	cam.shutter_speed=shutter
	# Enable with Picamera 1.6
	#if drc in cam.DRC_STRENGTHS.keys():
	#    cam.drc_strength = drc
	#else:
	#    cam.drc_strength = 'off'
	if effect in cam.IMAGE_EFFECTS:
	    cam.image_effect = effect
	else:
	    cam.image_effect = 'none'
	cam.vflip=True
	
def close_cam():
	cam.close()

def take_picture():
	""" 
	Returns an openCV compatible colour image 
	"""
	with picamera.array.PiRGBArray(cam) as output:
	    cam.capture(output, format='bgr')
	    return output.array
        
def take_bracket_pictures():
	""" 
	Returns two images in a list
	One with normal exposure, and one with 2 stop longer exposure 
	The aim to to get detail out of shadows/underexposed film
	Resulting images can be combined on a PC with Hugin's enfuse utility
	"""
	old_shutter = cam.shutter_speed
	imgs = []
	with picamera.array.PiRGBArray(cam) as output:
	    cam.capture(output, format='bgr')
	    imgs.append( output.array )
	    cam.shutter_speed = old_shutter*4
	    output.truncate(0)
	    cam.capture(output, format='bgr')
	    imgs.append( output.array )
	cam.shutter_speed = old_shutter
	return imgs
	
