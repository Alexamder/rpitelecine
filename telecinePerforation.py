# RPi Telecine - Perforation finding and detection#"""
#
# Perforation location and frame extraction for Super 8 and
# Standard 8 film.
# 
# This has been tested using Super8 amateur film with 
# black film base, commercial 8mm film with a clear film base.
# 
# Quite a few assumtions are made with regards to the position of
# each perforation in the frame - that they lie in the left hand 
# side of the frame - Super 8 perforations are situated in the
# middle vertically, and Standard 8 perforations are towards the
# top of the frame. A single perforation is used to extrapolate 
# the size of the crop. The film gate holds the film horizontally
# with little movement laterally.
#
# The first perforation found is used to extrapolate the other metrics 
# used for locating subsequent perforations, for trimming the ROI and
# finally for cropping.
# 
# The second is simpler, but tends to be more accurate in locating the vertical
# position and size of the hole. Less computation is required. If this one fails to the
# hole, the first method is tried. 
# 
# In practice the combination of methods seems to be pretty reliable and seems to
# cope reasonably well with hairs and minor damage in the sprocket holes.
# 
# Once a single perforation is detected, the size can be fixed, and its position set
# only from the top edge, and/or right hand edge of the perforation.
#
# This code could be adapted for 9.5mm film, with a change of ROI to the top centre
# of the film, though care would be needed not to include much of the image area.
#
# A more complex method based on the openCV squares.py example program was tried - 
# and was pretty successful, but ran very slowly on the Raspberry Pi, and not 100% reliable
# so this simpler method was chosen instead.
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
import numpy as np
import cv2
import scipy.ndimage.measurements as nd
from scipy import stats
from telecineImgproc import display_image


class telecinePerforation():
    """
    Class that handles the perforation finding, ROI
    """
    film_types = ['super8', 'std8']
    film_type = ''
    
    # Fuzz factor used in weeding out false positives
    size_margin = 0.2
    # Aspect ratio of the perforations
    perf_aspect = {'super8':(0.91/1.14), 'std8':(1.8/1.23)}

    # Frame size in proportion to the perforation size
    # Used to automatically crop. Width is assumed to be 1.33 x height 4:3 aspect
    # The calculations are based on the mm specification
    frame_height_mult = {'super8':(4.23/1.143), 'std8':(3.81/1.23)}
    frame_width_mult = {'super8':(5.46/0.91), 'std8':(4.5/1.8)}
    
    size = [0,0]	# Expected size of perforation
    
    ROI = None     # Slice for the ROI of the different finding methods
    img_size = (0,0) # Size of the frame to convert
 
    # Used as temporary image holder when detecting perforation
    roi_img = None
    
    cx = 0	# centre x line of perforation strip
    roi_cy = 0	# Centre y position in ROI
    
    # These are updated when the find method is called
    found = False	# If last detection was successful
    perforation = [0,0,0,0] # Last successfully found perforation - [x,y,w,h]
    prev_perforation = [0,0,0,0] # Previously successfully found perforation - [x,y,w,h]
    
    cy = 0	# centre y position of last found perforation
    perf_r = 0	# Right hand edge of perforation. Use this if horizontal registration is a problem
    y_diff = 0	# Difference between real and ideal position of perforation

    
    def __init__(self, film_type='super8', size = None, cx = 0):
	# cx is the perforation film line
	# size is a (w,h) tuple of a perforation size
	self.set_film_type(film_type)
	if size:
	    self.set_size(size)
	if cx>0:
	    self.cx = cx
	    
    def set_film_type(self, film_type):
	if film_type in self.film_types:
	    # Set aspect ratio bounds
	    self.film_type = film_type
	    self.aspect = self.perf_aspect[film_type]
	    self.aspect_min = self.aspect - (self.aspect * self.size_margin)
	    self.aspect_max = self.aspect + (self.aspect * self.size_margin)
	    self.size = None
	else:
    	    raise Exception("Error - '{}' is an incorrect film type.".format(film_type))
 
    def set_size(self,size):
	# Set bounds for expected size of perforation based on fuzz factor
	w,h = size
	if w>0 and h>0:
	    w_margin = w*self.size_margin
	    h_margin = h*self.size_margin
	    self.w_min, self.w_max = w-w_margin , w+w_margin
	    self.h_min, self.h_max = h-h_margin , h+h_margin
	    self.size = size
	else:
    	    self.expected_size = [0,0]
	    print("Warning - {} incorrect expected perforation size: ".format(size))

    def crop_slice(self,crop):
	"""
	Returns a numpy slice from a list/tuple (x,y,w,h)
	"""
	if len(crop)==4:
	    x,y,w,h = crop
	    x = max(x,0)
	    y = max(y,0)
	    w = max(w,1)
	    h = max(h,1)
	    return np.index_exp[ y:y+h, x:x+w ]
	else:
	    raise Exception('Error - incorrect crop {} given to crop_slice'.format(crop))

	    
    def set_roi(self,cx=0, perf_size=(0,0), img_size=(0,0) ):
	""" Sets the ROI based on image size, expected size and film type
	perf_size is a tuple of the (w,h) perforation size
	img_size is a tuple with the size of the image (w,h) or (h,w)
	Assumes a landscape image where the largest of the two is the width
	"""
	if cx > 0 and perf_size != (0,0):
	    self.cx = cx
	    self.size = perf_size
	    # Set height to half of image, and set y position depending of film format
	    img_h,img_w = img_size
	    if img_h>img_w:
		img_w,img_h = img_size
	    self.img_size = (img_w,img_h)
	    h = img_h // 2  # Use 1/2 of image height for ROI
	    if self.film_type == 'super8':
		# Middle of image height
		y = (img_h//2) - (h//2)
	    else:
		# Standard 8 - top part of image
		y = 75
	    self.roi_cy = y+h//2
	    # Set ROI width based on perforation size allowing a margin either side
	    w = int(1.2 * (perf_size[0]/2) ) 	# Allow for up to 20% margin either side of perforation
	    roi_l = max( cx - w, 0 )	# Left extent of ROI
	    roi_r = min( cx + w, img_w)	# Right extent of ROI
	    self.ROI = np.index_exp[ y:y+h, roi_l:roi_r ] # Slice object for making the ROI
	else:
	    self.ROI = None
	    raise Exception('Error - cannot set ROI')

    def find_perf_edges(self,img,coord,margin=80):
	""" 
	Take the coords (x,y) as a starting point, locate the top, bottom,
	left and right edges. Assumes the edges will be darker than the
	(x,y) point. 
	img is single channel grayscale version of the full image 
	but if converted first if necessary.
	margin is the number of pixels centred in the coord to smooth
	If a suitable bright area is found, the attributes describing
	the perforation are set, allowing find_perf_y to be used
	"""
	if len(img.shape) != 2:
	    img = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
	x,y = coord # Centre point to search from
	margin = margin//2
	
	# Make a full range image with values between 0 and 1.0
	roi =(img-img.min())/(img.max()-img.min()).astype(np.float32)

	# Mean value of frame border centred on x coord.
	thresh = roi[:,x-margin:x+margin].mean()
	thresh = thresh + ( (1.0 - thresh) / 5.0 )
	
	print "Thresh",thresh

	# Test the area around the starting coord for pixels below mean level
	test_location = (roi[y-margin:y+margin,x-margin:x+margin] < thresh).any()
	#print "Test location",test_location
	if test_location:
	    # we're too close an edge or not in the perforation at all
	    perforation = [0,0,0,0]
	    return False, perforation
	# Bottom segment
	# Get a slice from y to the bottom of the roi, with width pixels left and right 
	# Average across the width to get a 1d array and threshold it
	# Repeat for each segment
	thr = roi[y:,x-margin:x+margin].mean(axis=1) < thresh
	# Position of transition to dark edge
	m = thr.argmax() 
	print thr
	if m==0: m=len(thr) # If not found assume it's at the edge
	b = y + m
	# Top segment
	thr = roi[:y,x-margin:x+margin].mean(axis=1) < thresh
	m = thr[::-1].argmax() # count backwards
	if m==0: m=y
	t = y - m
	# Right hand segment
	thr = roi[y-margin:y+margin,x:].mean(axis=0) < thresh
	m = thr.argmax()
	if m==0: m=len(thr)
	r = x + m
	# Left hand segment
	thr = roi[y-margin:y+margin,:x].mean(axis=0) < thresh
	m = thr[::-1].argmax()
	#print "m:%d"%(m)
	if m==0: m=x
	l = x - m
	w,h = (r-l, b-t)
	# Set perforation information
	perforation = [l,t,w,h]
	return True, perforation
    
    def find_perf_y(self,img,margin=80):
	""" 
	Locate vertical position of a perforation
	img should be an ROI slice of the full image. 
	"""
	if len(img.shape) != 2:
	    # Convert to greyscale if necessary
	    img = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
	cx = img.shape[1] // 2	# Centre vertical line of image
	#print img.shape
	#print "ROI xy:{}:{}".format(self.ROI[1].start,self.ROI[0].start)
	margin = margin // 2
	#h_margin = int(round(self.size[1]*0.05)) # Allow +/- 5y% margin for height of perforation
	#h_min, h_max = self.size[1]-h_margin, self.size[1]+h_margin
	
	# Make a 1d array with the average values across the x axis over margin*2 pixels across
	roi = np.median(img[:,cx-margin:cx+margin],axis=1)
	# Scipy's mode can be used get the most common value
	# Might be better but adds seconds to each frame :-(
	#roi,counts = stats.mode(img[:,cx-margin:cx+margin],axis=1)
	
	# Make it full range with values between 0 and 1.0
	roi_min = roi.min()
	roi_max = roi.max()
	candidate = None
	if roi_min != roi_max:
	    # Prevent a divide by zero because roi is all the same value. 
	    # e.g. we have a frame completely white or black
	    roi =(roi-roi.min())/(roi.max()-roi.min()).astype(np.float32)
	    print "Mean-roi:",roi.mean()
	    thresh = roi.mean()
	    thresh = thresh + ( (1.0 - thresh) / 5.0 )
	    print 'Thresh',thresh
	    thr = roi > thresh
	    lbl,num_lbl = nd.label(thr)
	    obj = nd.find_objects(lbl)
	    
	    # And filter the objects that are close to the top/bottom and are too small/large
	    # Ideally we shouldn't have more than a few total, leading to a single candidate
	    end_point = len(thr)-margin
	    brightest = 0
	    for s in obj:
		# s is an np.slice object
		bright = roi[s].mean()
		s_height = s[0].stop - s[0].start
		#print('s_height:%d bright:%.3f'%(s_height,bright))
		#print('h_min:%d h_max:%d'%(self.h_min,self.h_max))
		if (s[0].start >= margin) and (s[0].stop <= end_point) and\
		    (self.h_min <= s_height <= self.h_max) and bright > brightest:
		    brightest = bright
		    candidate = s[0]

	if candidate:
	    found = True
	    x = cx-(self.size[0]//2)
	    y = candidate.start
	    w = self.size[0]
	    #h = candidate.stop - candidate.start
	    h = self.size[1]
	    perforation = [x,y,w,h]
	else:
	    found = False
	    perforation = []

	return found,perforation

    def tune_right_edge(self,img,cy,margin=80):
	""" 
	Fine tune right hand edge detection
	img is a greyscale ROI, cy is the vertical line of the perforation
	"""
	cx = img.shape[1] // 2
	margin = margin//2
	w_half = self.size[0]//2
	w_margin = int(round(w_half*0.2)) # Allow +/- 20% margin for adjusting
	w_min, w_max = w_half-w_margin, w_half+w_margin

	# Make a full range image with values between 0 and 1.0
	roi =(img-img.min())/(img.max()-img.min()).astype(np.float32)

	# Mean value of frame border centred on x coord.
	thresh = img[:,cx-margin:cx+margin].mean()
	thresh = thresh + ( (1.0 - thresh) / 5.0 )
	#print 'w_min:{} w_max:{}, Thresh:{}'.format(w_min,w_max,thresh)
	    	
	# Right hand segment
	thr = img[cy-margin:cy+margin,cx:].mean(axis=0) < thresh
	#print thr
	m = thr.argmax()
	if m==0: m=len(thr)
	r = cx + m
	return w_min <= m <= w_max, r
	
    def find(self,img):
	""" 
	Finds the perforation
	Requires the centre x line, expected perforation size to be set
	
	"""
	if self.ROI == None:
	    # Set ROI
	    raise Exception('Error - ROI not set before perforation finding')
	if self.found:
	    # If we previously found a perforation, save it
	    self.prev_perforation = self.perforation
	
	if len(img.shape)>2:
	    # Make grey
	    self.roi_img = cv2.cvtColor(img[self.ROI],cv2.COLOR_BGR2GRAY)
	else:
	    self.roi_img = img[self.ROI]
	margin = int(self.size[0]*0.7)
	found,perforation = self.find_perf_y(self.roi_img,margin)
	
	self.found = found
	if found:
	    x = perforation[0]+self.ROI[1].start
	    y = perforation[1]+self.ROI[0].start
	    w,h = self.size
	    self.perforation = [x,y,w,h]
	    self.cy = y + (h//2)
	    self.y_diff = self.cy - self.roi_cy # Difference between measured and ideal position
	    self.perf_r = x + w
	else:
	    self.perforation = [0,0,0,0]
	    self.cy = 0
	    self.perf_r = 0
	    self.y_diff = 0
	return found	    
	
if __name__ == '__main__':
    # Test - find perforations in a folder load of images
    # TODO rewrite for current implementation
    pass