# RPi Telecine Configuration
#
# Config file handling for the telecine scripts 
# Provides for reading and writing the job's ini file
#
# Copyright (c) 2015, Jason Lane
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
import ConfigParser



class TelecineConfig():
    
    config = ConfigParser.SafeConfigParser()
    film_type = 'super8'

    shutter_speed = 0
    awb_gains = [1.5,1.5]
    show_gray = False
    brackets = False
    
    # Dynamic Range Compression
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
	

