# RPi Telecine PySide based control
#
# Provides a class that interfaces with the RPiTelecine controller PCB.
# A thread is used to operate the motors in the background and to keep the 
# user interface responsive.
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

import time
from PySide import QtCore, QtGui 
from rpiTelecine import ( StepperMotor,ReelMotor,LedControl, ShutterRelease )
import wiringpi2 as wiringpi

FORWARD  = True
BACKWARD = False

class Stepper(QtCore.QObject):
    # Designed to run in a thread
    # Handles the control and synchronising of the motors on the telecine machine.
    # Film can be moved backwards and forwards, and the spools moved on a 
    # regular basis.
    # This class uses counters to keep the film wound onto the takeup spools
    # and counters are used to prevent film bunching up before the gate.

    finished = QtCore.Signal()          # emitted when stepcounter reaches zero
    whileStepping = QtCore.Signal()     # emitted periodically when stepping

    steps = 0
    exiting = False
    quiet = False # suppress signals while true
    winding = False # Fast rewind mode
    fourStepper = False # Use pulsed DC motors or steppers for film spools

    updateCount = 50    # Steps between sending whileStepping signal
    tensionCount = 50   
    takeUpCount = 600   # Steps between moving the film takeup spool
    spoolCount = 3      # Move the film spool every spoolCount steps of the takeup spool

    def __init__(self,m1,m2,m3,m4):
        super( Stepper, self ).__init__()
        self.m1 = m1
        self.m2 = m2
        self.m3 = m3
        self.m4 = m4
        self.direction = FORWARD
        self.setDirection()

    def run(self):
        m1 = self.m1   # Speed up loop a bit by not evaluating dots
        m2 = self.m2
        m3 = self.m3
        m4 = self.m4
        self.fourStepper = ( type(m3) == type(m4) == StepperMotor )
        updateCounter = self.updateCount
        self.tensionCounter = self.tensionCount
        takeUpCounterFwd = 0
        takeUpCounterBack = 0
        self.spoolCounter = 0
        print "starting runner"
        while not self.exiting:
            time.sleep(0.05)
            while self.steps > 0:
                if self.direction:
                    # FORWARD
                    takeUpCounterFwd = self.doStep( m1,m2,m3,m4,takeUpCounterFwd )
                else:
                    # BACKWARD
                    takeUpCounterBack = self.doStep( m2,m1,m4,m3,takeUpCounterBack )
                updateCounter -= 1
                if updateCounter < 1:
                    updateCounter = self.updateCount
                    if not self.quiet:
                        self.whileStepping.emit()
                self.steps -= 1
                if not(self.quiet) and self.steps < 1:
                    print("Emitting Finished stepping signal")
                    self.finished.emit()
            while self.winding:
                # Fast Rewind or wind on film spool motors only
                if self.fourStepper:
                    if self.direction:
                        self.doWind( m3,m4 )
                    else:
                        self.doWind( m4,m3 )
                else: 
                    time.sleep(0.01)
                updateCounter -= 1
                if updateCounter < 1:
                    updateCounter = self.updateCount
                    if not self.quiet:
                        self.whileStepping.emit()

    def doStep(self, m1,m2,m3,m4,takeUpCounter):
        # push film one step
        if self.tensionCounter > 0:
            m1.step()
            self.tensionCounter -= 1
        else:
            # but break occasionally to stop film bunching before the gate
            self.tensionCounter = self.tensionCount
        # Pull film one step
        m2.step()
        takeUpCounter -= 1
        if takeUpCounter < 1:
            takeUpCounter = self.takeUpCount
            if self.fourStepper:
                # Using two steppers for film takeup spools - run the takeup
                # spool three times as fast as the unloading spool
                # Untested as yet - will need to check on a working device
                self.spoolCounter -= 1
                if self.spoolCounter < 1:
                    self.spoolCounter = self.spoolCount
                    m3.step()
                m4.step()
            else:
                # Using DC motors - pulse
                m4.pulse()
        return takeUpCounter
    
    def doWind(self,m3,m4):
        self.spoolCounter -= 1
        if self.spoolCounter < 1:
            self.spoolCounter = self.spoolCount
            m3.step()
        m4.step()        

    def setDirection(self):
        d = self.direction
        self.m1.set_direction(d)
        self.m2.set_direction(d)
        if self.fourStepper:
            self.m3.set_direction(d)
            self.m4.set_direction(d)
            
    @QtCore.Slot(bool)
    def setQuietMode(self,quiet = True):
        self.quiet = quiet
        if quiet:
            print( "Setting Quiet Mode")
        else:
            print( "Removing Quiet Mode")

    @QtCore.Slot()
    def stopStepping(self):
        self.steps = 0
        if self.winding:
            self.stopWinding()

    @QtCore.Slot(int)
    def stepForward(self, steps):
        if self.direction != FORWARD:
            self.direction = FORWARD
            self.setDirection()
            self.steps = 0
        self.steps += steps
        self.winding = False

    @QtCore.Slot(int)
    def stepBackward(self, steps):
        if self.direction != BACKWARD:
            self.direction = BACKWARD
            self.setDirection()
            self.steps = 0
        self.steps += steps
        self.winding = False

    @QtCore.Slot()
    def tensionFilm(self):
        # Run pulley motors in opposite directions to tension film
        self.stopStepping()
        time.sleep(0.1)
        self.m1.set_direction(BACKWARD)
        self.m2.set_direction(FORWARD)
        for step in xrange(1,20):
            self.m1.step()
            self.m2.step()
        self.setDirection()

    @QtCore.Slot()
    def close(self):
        print "Closing"
        self.stopWinding()
        self.steps = 0
        self.exiting = True

    @QtCore.Slot()
    def rewind(self):
        self.steps = 0 # Stop stepping as a precaution
        self.direction = BACKWARD
        self.setDirection()
        self.winding = True
        if not self.fourStepper:
            self.m3.on()
            self.m4.off()

    @QtCore.Slot()
    def windOn(self):
        self.steps = 0 # Stop stepping as a precaution
        self.direction = FORWARD
        self.setDirection()
        self.winding = True
        if not self.fourStepper:
            self.m3.off()
            self.m4.on()

    @QtCore.Slot()
    def stopWinding(self):
        self.steps = 0
        self.winding = False
        if not self.fourStepper:
            self.m3.off()
            self.m4.off()

    @QtCore.Slot(int)
    def setUpdateCount( self,n ):
        self.updateCount = n

    @QtCore.Slot(int)
    def setTensionCount( self,n ):
        self.tensionCount = n

    @QtCore.Slot(int)
    def setTakeUpCount( self,n ):
        self.takeUpCount = n

    @QtCore.Slot(int)
    def setSpoolCount( self,n ):
        self.spoolCount = n

class GuiTelecineControl(QtCore.QObject):

    pinBase = 100
    pins = { 'm1Enable':pinBase,   'm1Step':pinBase+1, 'm1Dir':pinBase+2, 
             'm2Enable':pinBase+5, 'm2Step':pinBase+4, 'm2Dir':pinBase+3,
             'reel1':pinBase+6,    'reel2':pinBase+7,  'led':pinBase+8,
             'shutter':pinBase+9,  'focus':pinBase+10, 'm34enable':pinBase+11,
             'm3Step':pinBase+12,  'm3Dir':pinBase+13, 'm4Dir':pinBase+14,
             'm4Step':pinBase+15 }

    fourStepper = False 
    # If true, use two steppers for the film spools, otherwise use the DC motors

    stepperThread = QtCore.QThread()

    def __init__(self, MCPaddress=0, useFourStepper=False):
        super(GuiTelecineControl,self).__init__()
        wiringpi.wiringPiSetupSys()
        wiringpi.mcp23s17Setup(self.pinBase, 0, MCPaddress) 
        pin = self.pins

        # Stepper Motors
        self.m1 = StepperMotor(pin['m1Step'],pin['m1Dir'],pin['m1Enable'])
        self.m2 = StepperMotor(pin['m2Step'],pin['m2Dir'],pin['m2Enable'])

        self.setFourStepper( useFourStepper )

        # Set up the thread to allow film to be moved in background
        self.stepperWorker = Stepper(self.m1,self.m2,self.m3,self.m4)
        self.stepperWorker.moveToThread(self.stepperThread)
        self.stepperThread.started.connect( self.stepperWorker.run )
        self.stepperThread.start()

        # Make stepperWorker slots members of the GuiTC object
        sw = self.stepperWorker
        self.stepBackward = sw.stepBackward
        self.stepForward = sw.stepForward
        self.tensionFilm = sw.tensionFilm
        self.stopStepping = sw.stopStepping
        self.setQuietMode = sw.setQuietMode
        self.finishedStepping = sw.finished
        self.whileStepping = sw.whileStepping
        self.rewind = sw.rewind
        self.windOn = sw.windOn
        self.stopWinding = sw.stopWinding
        self.setUpdateCount = sw.setUpdateCount
        self.setTensionCount = sw.setTensionCount
        self.setTakeUpCount = sw.setTakeUpCount
        self.setSpoolCount = sw.setSpoolCount
        
        # LED control
        self.led = LedControl(pin['led'])
        self.led.on()
        
        # Shutter release
        self.shutterRelease = ShutterRelease(pin['focus'], pin['shutter'])

    def setFourStepper(self,useFourStepper=False):
        self.fourStepper = useFourStepper
        pin = self.pins
        if self.fourStepper:
            self.m3 = StepperMotor(pin['m3Step'],pin['m3Dir'],pin['m34Enable'])
            self.m4 = StepperMotor(pin['m4Step'],pin['m4Dir'],pin['m34Enable'])
        else:
            # DC motors for takeup reels
            self.m3 = ReelMotor(pin['reel1'])
            self.m4 = ReelMotor(pin['reel2'])

    # LED control

    @QtCore.Slot()
    def ledOn(self):
        self.led.on()

    @QtCore.Slot()
    def ledOff(self):
        self.led.off()

    @QtCore.Slot(bool)
    def LED(self,state):
        if state:
            self.led.on()
        else:
            self.led.off()

    @QtCore.Slot()
    def releaseWake(self):
        self.shutterRelease.wake_camera()

    @QtCore.Slot()
    def releaseTrigger(self):
        self.shutterRelease.fire_shutter()

    @QtCore.Slot(bool)
    def enableSteppers(self,en=True):
        if en:
            self.m1.on()
            self.m2.on()
            if self.fourStepper:
                self.m3.on()
        else:
            self.m1.off()
            self.m2.off()
            if self.fourStepper:
                self.m3.off()


    def cleanUp(self):
        self.stepperWorker.close()
        self.stepperThread.exit()
        self.stepperThread.wait()
        self.led.off()
        # De-energise steppers
        self.enableSteppers( False )
