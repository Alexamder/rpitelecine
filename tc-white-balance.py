#!/usr/bin/env python
#
# RPi Telecine Camera Setup Whitebalance setting
#
# Obtain base white balance and shutter speed for the telecine.
#
# A simple program that swiches on the light, waits a bit
# for the LEDs to warm up, then takes a Jpeg image in a 
# stream object. It uses the Exif data stored by the  
# Pi camera to obtain the shutter speed and white balance
# This is needed to fix the exposure and colour for the 
# telecine job.
#
# It's a good idea to run this whenever the lighting settings
# are altered. Also found that a good shutter speed is obtained
# by putting a 2 stop neutral density filter in front of the
# lightbox diffuser
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


import io
import os
import time
import ConfigParser
import picamera

import rpiTelecine

def get_awb_shutter( f ):
    """ 
    Get AWB and shutter speed from file object 
    This routine extracts the R and B white balance gains and the shutter speed
    from a jpeg file made using the Raspberry Pi camera. These are stored as text in 
    a custom Makernote.
    The autoexposure and AWB white balance values are not available directly until
    a picture is taken and are saved in a Jpeg. 
    Returns 0 for the values if they're not found
    """
    f.seek(256)
    s = f.read(512) # Only part of the header needed
    r_pos = s.find('gain_r=')
    b_pos = s.find('gain_b=')
    s_pos = s.find(' exp=')
    gain_r = eval(s[r_pos+7:r_pos+12].split()[0]) if r_pos > -1 else 0
    gain_b = eval(s[b_pos+7:b_pos+12].split()[0]) if b_pos > -1 else 0
    shutter = eval(s[s_pos+5:s_pos+12].split()[0]) if s_pos > -1 else 0
    return (gain_r,gain_b,shutter)

configname = os.path.expanduser('~/.telecine.ini')

tc =  rpiTelecine.tcControl()
tc.light_on()

print('Warming up lamp...')

# Create an in-memory stream
stream = io.BytesIO()
with picamera.PiCamera() as camera:
    camera.shutter_speed = 0
    camera.exposure_mode = 'auto'
    camera.awb_mode = 'flash'
    camera.resolution = (2592,1944)
    camera.crop = (0.25,0.25,0.25,0.25)
    camera.ISO = 100
    camera.vflip = True
    camera.start_preview()
    camera.preview_fullscreen=True
    # Camera warm-up time - and allow time for WB to settle
    time.sleep(20)
    camera.capture(stream, 'jpeg')
tc.light_off()

stream.seek(0)
gain_r,gain_b,shutter_speed = get_awb_shutter(stream)

print("Gain_r:{:.3f} Gain_b:{:.3f} Shutter:{}".format(gain_r,gain_b,shutter_speed )) 

# Write config file
print('Writing config file {}'.format(configname))

config = ConfigParser.ConfigParser()
with open(configname,'w') as f:
	config.add_section('Telecine')
	config.set('Telecine','gain_r',gain_r)
	config.set('Telecine','gain_b',gain_b)
	config.set('Telecine','shutter_speed',shutter_speed)
	config.write(f)
