#!/bin/sh
# Just calls Raspistill to show the camera preview
# Useful for setting focus
raspistill -fp -ex backlight -awb auto -vf -k -ISO 100  -t 9000 
