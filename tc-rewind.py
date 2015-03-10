#!/usr/bin/env python
#
# RPi Telecine rewind
# Runs the rewind motor for 150 seconds. Enough for a 50ft reel
# Just helps rewind the film.

import time
import argparse
import rpiTelecine

parser = argparse.ArgumentParser(description='Rewind or wind the film. Only the reel motors are activated.')
parser.add_argument('-s','--seconds', action="store", default='20', dest='seconds', type=int, help='Seconds to wind. Default 20')
parser.add_argument('-f','--forwards', action="store_const", const=True, default=False, dest='forwards', help='Wind forwards')

args = parser.parse_args()

tc =  rpiTelecine.tcControl()
tc.light_off()

try:
    if args.forwards:
        tc.reel2.on()
    else:
        tc.reel1.on()
    time.sleep( args.seconds )
finally:
    tc.reel1.off()
    tc.reel2.off()
    tc.clean_up()
