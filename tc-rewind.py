#!/usr/bin/env python
#
# RPi Telecine rewind
# Runs the rewind motor for 150 seconds. Enough for a 50ft reel
# Just helps rewind the film.

from __future__ import division
import time
import telecineControl

tc =  telecineControl.tcControl()
tc.light_off()


try:
	tc.reel1.on()
	time.sleep(150)        
finally:
	tc.reel1.off()
	tc.clean_up()
