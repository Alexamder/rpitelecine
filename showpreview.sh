#!/bin/sh
# Just calls Raspistill to show the camera preview
# Useful for setting focus
raspistill -fp -ex backlight -awb auto -vf -k -roi 0.4,0.33,0.33,0.33 -ISO 100  -t 9000 
