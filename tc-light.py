#!/usr/bin/env python
#
# RPi Telecine rewind
# Runs the rewind motor for 150 seconds. Enough for a 50ft reel
# Just helps rewind the film.

import time
import argparse
import rpiTelecine

parser = argparse.ArgumentParser(description='Control the light')
action = parser.add_mutually_exclusive_group(required=True)
action.add_argument('-1','--on', action='store_true', help='Light On')
action.add_argument('-0','--off', action='store_true', help='Light Off')

args = parser.parse_args()

tc =  rpiTelecine.tcControl()
if args.on:
    print('Light on')
    tc.light_on()
if args.off:
    print('Light off')
    tc.light_off()
