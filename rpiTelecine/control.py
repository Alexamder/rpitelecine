# RPi Telecine - Controller board 
#
# Code to encapsulate the operation of the controller board
#	
# The telecine board uses an MCP23S17 digital IO expander to control:
# 	2x stepper motors in microstepping mode using  BigEasyDriver modules
# 	2x geared motors for film reel takeup
# 	Power LED to illuminate film
# 	External camera shutter release circuit using 2 opto-couplers.
# 	Remaining pins on the MCP23S17 are broken out for future use and
# 	can be used as GPIOs
# 	
# Version 1 of the PCB is 10x10cm with pin headers for the motors,
# 2 x power LEDs, Raspberry Pi model B and GPIO. Wiringpi2 is used
# for control. The PCB takes a 3A+ 12V power supply, and provides
# power for the Pi using the 5V pin of the Pi's GPIO header.
# For the two power LEDs, XPPower LDU0516S350 (or similar with
# identical pinout) are used. These allow a control voltage to
# adjust the brightness - so they can be trimmed on the board. 
# The PCB uses a LM2596 adjustable buck converter (Check that it
# outputs 5V before connecting the Pi!), and Big Easy Drivers for the
# stepper motors. The BEDs, although expensive, allow the microstepping
# required for the film transport.
# The LED power and DC motors are switched using Mosfets.
#
# Prerequisites: 
#   Wiringpi2 for Python
#   SPI needs to be enabled from raspi-config so the correct kernel 
#   modules are loaded on boot.
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
from wiringpi2 import *
import time

class TelecineControl():
    
    pin_base=100
    m1_en_pin = pin_base+0
    m1_step_pin = pin_base+1
    m1_dir_pin = pin_base+2
    m2_en_pin = pin_base+5
    m2_step_pin = pin_base+4
    m2_dir_pin = pin_base+3
    reel1_pin = pin_base+6
    reel2_pin = pin_base+7
    led_pin = pin_base+8
    shutter_pin = pin_base+9
    focus_pin = pin_base+10
    gpio1_pin = pin_base+11
    gpio2_pin = pin_base+12
    gpio3_pin = pin_base+13
    gpio4_pin = pin_base+14
    gpio5_pin = pin_base+15
    
    
    # Parameters to pulse takeup reel every so often to keep film
    # wrapped around rollers
    take_up_steps = take_up_counter = 550
    
    # Because of slippage in system skip pushing film every so often
    # Without this, film tends to start to slacken and bunch up
    # before the gate. 
    tension_steps = 50
    step_counter = 0
    
    def __init__(self):
	wiringPiSetupSys()
	mcp23s17Setup(self.pin_base, 0, 0) 
	# Stepper Motors
	self.m1 = StepperMotor(self.m1_step_pin, self.m1_dir_pin, self.m1_en_pin)
	self.m2 = StepperMotor(self.m2_step_pin, self.m2_dir_pin, self.m2_en_pin)
	# DC motors for takeup reels
	self.reel1 = ReelMotor(self.reel1_pin)
	self.reel2 = ReelMotor(self.reel2_pin)
	# LED control
	self.led = LedControl(self.led_pin)
	# Shutter release
	self.shutter_release = ShutterRelease(self.focus_pin, self.shutter_pin)
	self.m1.on()
	self.m2.on()
	# Direction of film travel - 
	# Forward: True = m1 to m2 False = m2 to m1
	self.m1.set_direction(True)
	self.m2.set_direction(True)
	self.direction = True
	
    def light_on(self):
	self.led.on()
	
    def light_off(self):
	self.led.off()
	
    def change_direction( self, d = True ):
	"""
	Set parameters when direction changes
	"""
	self.direction = d
	self.take_up_counter = self.take_up_steps
	self.step_counter = self.tension_steps
	self.m1.set_direction(d)
	self.m2.set_direction(d)

    def steps_forward(self,steps=1):
	""" 
	Take steps forward - pulse the takeup reel and tension film
	by ignoring push step occasionally
	"""
	m1step = self.m1.step	# Speed up loop a bit by not evaluating dots
	m2step = self.m2.step
        if not self.direction:
            self.change_direction( True )
	while steps>1:
            steps -= 1
	    self.take_up_counter -= 1
            if self.take_up_counter==1:
                self.reel2.pulse()
                self.take_up_counter=self.take_up_steps
	    if self.step_counter>0:
		# Push film one step
		m1step()
		self.step_counter -= 1
	    else:
		# Skip pushing
		self.step_counter = self.tension_steps
	    # Pull film one step
	    m2step()
    
    def steps_back(self,steps=1):
	""" 
	Take steps backwards
	"""
	m1step = self.m1.step	# Speed up loop a bit by not evaluating dots
	m2step = self.m2.step
        if self.direction:
            self.change_direction( False )
        while steps>1:
            steps -= 1
	    self.take_up_counter -= 1
	    if self.take_up_counter==0:
                self.reel1.pulse()
                self.take_up_counter=self.take_up_steps
	    if self.step_counter>0:
		m2step()
		self.step_counter -= 1
	    else:
		self.step_counter = self.tension_steps
	    m1step()	


    def tension_film(self,steps=200):
	# Run steppers in opposite direction for a short period - Tightens up the film
	d = self.direction
	self.m1.set_direction(False)
	self.m2.set_direction(True)	
	for n in xrange(steps):
	    self.m1.step()	
	    self.m2.step()	
	self.m1.set_direction(d)
	self.m2.set_direction(d)

    
    def clean_up(self):
	# Switch things off to tidy up
	self.led.off()
	self.reel1.off()
	self.reel2.off()
	self.m1.off()
	self.m2.off()
	
class StepperMotor():
			
    """
    Simple Stepper motor control class

    Simple class to control stepper motors
    using the BigEasyDriver
    http://www.schmalzhaus.com/BigEasyDriver/

    To control one motor these pins are used:

    EN - Enable/Energise the motor (optional)
    DR - Direction of step
    ST - Step
    GND - Ground connection

    Motor is energised by default - the EN pin can switch power to motor 
    off, to allow manual positioning etc. This connection is optional.

    Big Easy Driver defaults to 3200 steps per rotation, microstepping 
    mode. Re-energising the coils after sleeping will set the nearest 
    whole step
    """

    delay = 1 # Big Easy Driver requires a pulse of 1uS or longer.
    motor_on = False
    
   
    def __init__(self,step_pin,dir_pin,en_pin):
        
        self.step_pin = step_pin
        self.dir_pin = dir_pin
        self.en_pin  = en_pin
        pinMode( step_pin, 1 )         # Output
        pinMode( dir_pin, 1 )          # Output
        pinMode( en_pin, 1 )       	# Output
        self.on()
        self.direction = True
             
    def on(self):
        # enable motor - set motorOn flag
        digitalWrite(self.en_pin,False)
        self.motor_on = True
        
    def off(self):
        # if enable pin is used, de-energise the motor coils
        digitalWrite(self.en_pin,True)
        self.motor_on = False

    def set_direction( self,direction=True ):    
	# set Direction of motor - true=ccw; false=cw
	self.direction = 1 if direction else 0
	digitalWrite(self.dir_pin, self.direction)
        
    def step(self):
	# Make a step
	# Big Easy Driver will step when the pin rises
	# Should be on and off for at least 1uS 
	digitalWrite(self.step_pin,True)
	#delayMicroseconds(self.delay)
	digitalWrite(self.step_pin,False)
	#delayMicroseconds(self.delay)
        
    def steps(self,s):
        # Go s steps
        for i in xrange(0,s):
            self.step()

class LedControl:
    """
    Simple Class to control the LED power
    """

    def __init__(self,pin):
	self.pin = pin
	pinMode( pin, True )
	self.off()

    def on(self):
	digitalWrite( self.pin, True )

    def off(self):
	digitalWrite( self.pin, False )


class ReelMotor:
    """
	Class to control DC motors for film spools
	The motors are controlled simply by switching on a wiringpi pin
    """
    pulse_delay = 35/1000	# Pulse delay in milliseconds

    def __init__(self,pin):
	self.pin = pin
	pinMode( pin, True )
	self.off()

    def on(self):
	digitalWrite( self.pin, True )

    def off(self):
	digitalWrite( self.pin, False )

    def pulse(self):
	digitalWrite( self.pin, True )
	time.sleep(self.pulse_delay)
	#delay( self.pulse_delay )
	digitalWrite( self.pin, False )


class ShutterRelease():
    """
    Telecine SLR shutter release class

    Uses 2 pins with wiringPi2 - connected to a pair of opto-couplers
    and a cable to  2.5mm tip/ring/sleeve (stereo) jack used
    by Pentax and some Canon shutter release cables. Will probably
    work in a similar way using a different connector with other 
    cameras. This method is used a lot with Arduinos.
    The delay settings were established by trial and error with my own
    DSLR. There is opten quite a lag for the camera to start and take
    a picture.
    """
    
    wake_delay = 1500  # Delay in ms to wait for camera to wake up
    shutter_delay = 300 # Delay in milliseconds to hold shutter pin high 
    
    def __init__(self,focus_pin, shutter_pin):
        self.focus_pin = focus_pin
        self.shutter_pin = shutter_pin
        pinMode( focus_pin, 1 )          # Output
        pinMode( shutter_pin, 1 )          # Output
        digitalWrite(self.focus_pin,False)
        digitalWrite(self.shutter_pin,False)
        
    def wake_camera(self):
        digitalWrite(self.focus_pin,True)
        delay( self.wake_delay )
        digitalWrite(self.focus_pin,False)
          
    def fire_shutter(self):
        digitalWrite(self.shutter_pin,True)
        delay( self.shutter_delay )
        digitalWrite(self.shutter_pin,False)
        
        
# Test the hardware
if __name__ == '__main__':
    tc =  tcControl()
    tc.light_on()
    for j in range(1,15):
	delay(500)
	tc.steps_forward(310)
    delay(2000)
    for j in range(1,15):
	delay(500)
	tc.steps_back(310)	
    tc.clean_up()
    
	
