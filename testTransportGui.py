#!/usr/bin/env python

import sys
import os
import time
import atexit

from PySide.QtCore import QSettings
from PySide import QtCore, QtGui 

from rpiTelecine import ( StepperMotor,ReelMotor,LedControl, ShutterRelease )

import wiringpi2 as wiringpi

frameSteps = 314

FORWARD = True
BACKWARD = False

class Stepper(QtCore.QObject):
    # Designed to run in a thread
    # Handles the control of the motors on the telecine machine.
    # Film can be moved backwards and forwards through
    # This class uses counters to keep the film wound onto the takeup spools
    # and counters are used to prevent film 
    
    finished = QtCore.Signal()
    whileStepping = QtCore.Signal()
    
    steps = 0
    exiting = False
    quiet = False # suppress signals while true
    winding = False # Fast rewind mode
    fourStepper = False # Use pulsed DC motors or steppers for film spools
    
    updateCount =50
    tensionCount = 50
    takeUpCount = frameSteps * 4
    spoolCount = 3
    
    def __init__(self,m1,m2,m3,m4):
        super( Stepper, self ).__init__()
        self.m1 = m1
        self.m2 = m2
        self.m3 = m3
        self.m4 = m4
        self.direction = FORWARD
        self.setDirection()

    #@QtCore.Slot()
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
                self.steps -= 1
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
                if self.steps == 0 and not self.quiet:
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
    def setQuietmode(quiet = True):
        self.quiet = quiet

    @QtCore.Slot()
    def stopStepping(self):
        self.steps = 0
        if self.winding:
            self.stopWinding()

    @QtCore.Slot(int)
    def stepForward(self, steps):
        if self.direction == BACKWARD:
            self.direction = FORWARD
            self.setDirection()
            self.steps = 0
        self.steps += steps
        self.winding = False

    @QtCore.Slot(int)
    def stepBackward(self, steps):
        if self.direction == FORWARD:
            self.direction = BACKWARD
            self.setDirection()
            self.steps = 0
        self.steps += steps
        self.winding = False

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
            self.m4.off()
            self.m3.on()

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
            

class GuiTC(QtCore.QObject):

    pinBase = 100
    pins = { 'm1Enable':pinBase,   'm1Step':pinBase+1, 'm1Dir':pinBase+2, 
             'm2Enable':pinBase+5, 'm2Step':pinBase+4, 'm2Dir':pinBase+3,
             'reel1':pinBase+6,    'reel2':pinBase+7,  'led':pinBase+8,
             'shutter':pinBase+9,  'focus':pinBase+10, 'm34enable':pinBase+11,
             'm3Step':pinBase+12,  'm3Dir':pinBase+13, 'm4Dir':pinBase+14,
             'm4Step':pinBase+15 }

    fourStepper = False 
    # If true, use two steppers for the film spools, otherwise use the DC motors
    
    finishedSig = QtCore.Signal()
    runSig = QtCore.Signal()

    # Parameters for running the stepper motors
    
    runCount = 50
    runCounter = 10

    tensionSteps = 50
    tensionCounter = 0

    takeUpSteps = frameSteps * 4
    takeUpCounterFwd = 0
    takeUpCounterBack = 0
    
    stepperThread = QtCore.QThread()
    

    def __init__(self, MCPaddress=0, useFourStepper=False):
        super(GuiTC,self).__init__()
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
        self.stopStepping = sw.stopStepping
        self.setQuietmode = sw.setQuietmode
        self.finishedStepping = sw.finished
        self.whileStepping = sw.whileStepping
        self.rewind = sw.rewind
        self.windOn = sw.windOn
        self.stopWinding = sw.stopWinding

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

    
    

tc = GuiTC()

class TransportTest(QtGui.QWidget):
    
    def __init__(self):
        super( TransportTest, self).__init__()
        self.initUI()
        
        self.btnFwd.clicked.connect( lambda: tc.stepForward(frameSteps) )
        self.btnFwd.clicked.connect( lambda: self.updateStatus('Forward') )
        self.btnFFwd.clicked.connect( lambda: tc.stepForward(frameSteps*180) )
        self.btnFFwd.clicked.connect( lambda: self.updateStatus('Fast Forward') )
        self.btnBack.clicked.connect( lambda: tc.stepBackward(frameSteps) )
        self.btnBack.clicked.connect( lambda: self.updateStatus('Back') )
        self.btnFBack.clicked.connect( lambda: tc.stepBackward(frameSteps*180) )
        self.btnFBack.clicked.connect( lambda: self.updateStatus('Fast Backwards') )
        self.btnStop.clicked.connect( tc.stopStepping )
        self.btnLED.clicked.connect( self.toggleLight )
        self.btnLED.clicked.connect( lambda: self.updateStatus( 'LED {}'.format('on' if self.light else 'off' ) ) )
        tc.whileStepping.connect(self.updateSpinner)
        tc.finishedStepping.connect( lambda: self.updateStatus('Paused') )
        self.btnTrigger.clicked.connect( tc.releaseTrigger )
        self.btnTrigger.clicked.connect( lambda: self.updateStatus('Shutter Release triggered') )
        self.btnWake.clicked.connect( tc.releaseWake )
        self.btnWake.clicked.connect( lambda: self.updateStatus('Shutter Release wake') )
        self.btnEnable.clicked.connect( lambda: tc.enableSteppers( True ) )
        self.btnEnable.clicked.connect( lambda: self.updateStatus('Steppers Enabled') )
        self.btnDisable.clicked.connect( lambda: tc.enableSteppers( False ) )
        self.btnDisable.clicked.connect( lambda: self.updateStatus('Steppers Disabled') )
        self.btnWindOn.clicked.connect( tc.windOn )
        self.btnWindOn.clicked.connect( lambda: self.updateStatus('Fast Wind On') )
        self.btnRewind.clicked.connect( tc.rewind )
        self.btnRewind.clicked.connect( lambda: self.updateStatus('Fast Rewind') )
        self.btnStopWind.clicked.connect( tc.stopWinding )
        self.btnStopWind.clicked.connect( lambda: self.updateStatus('Stop winding') )
        


    def initUI(self):
        self.btnFwd = QtGui.QPushButton(">")
        self.btnBack = QtGui.QPushButton("<")
        self.btnFFwd = QtGui.QPushButton(">>")
        self.btnFBack = QtGui.QPushButton("<<")
        self.btnStop = QtGui.QPushButton("Stop")
        self.btnLED = QtGui.QPushButton("Light")
        self.btnWake = QtGui.QPushButton("SR Wake")
        self.btnTrigger = QtGui.QPushButton("SR Trigger")
        self.btnEnable = QtGui.QPushButton("Enable Steppers")
        self.btnDisable = QtGui.QPushButton("Disable Steppers")
        self.btnRewind  = QtGui.QPushButton("<<< Rewind")
        self.btnStopWind  = QtGui.QPushButton("Stop")
        self.btnWindOn  = QtGui.QPushButton("Wind on >>>")
        
        self.lblStatus = QtGui.QLabel("Paused")
        self.lblSpinner = QtGui.QLabel("|")
        hbox = QtGui.QHBoxLayout()
        hbox2 = QtGui.QHBoxLayout()
        hbox3 = QtGui.QHBoxLayout()
        hbox4 = QtGui.QHBoxLayout()
        hbox.addWidget(self.btnFBack)
        hbox.addWidget(self.btnBack)
        hbox.addWidget(self.btnStop)
        hbox.addWidget(self.btnFwd)
        hbox.addWidget(self.btnFFwd)
        hbox2.addWidget(self.btnLED)
        hbox3.addWidget(self.btnWake)
        hbox3.addWidget(self.btnTrigger)
        hbox4.addWidget(self.btnEnable)
        hbox4.addWidget(self.btnDisable)
        hbox5 = QtGui.QHBoxLayout()
        hbox5.addWidget(self.btnRewind)
        hbox5.addWidget(self.btnStopWind)
        hbox5.addWidget(self.btnWindOn)
        
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.lblStatus)
        vbox.addWidget(self.lblSpinner)
        vbox.addStretch(1)
        vbox.addLayout(hbox3)
        vbox.addLayout(hbox2)
        vbox.addLayout(hbox4)
        vbox.addLayout(hbox5)
        vbox.addLayout(hbox)        
        self.setLayout(vbox)
        self.setGeometry(300, 300, 300, 150)
        self.setWindowTitle("Test Transport")
        self.show()

    light = True

    spin = 0
    spinChars = '|\-/'
    
    @QtCore.Slot()
    def updateSpinner(self):
        self.lblSpinner.setText( self.spinChars[self.spin] )
        self.spin = (self.spin + 1) % len(self.spinChars)
        self.lblSpinner.repaint()
        QtCore.QCoreApplication.processEvents()
    
    @QtCore.Slot(str)
    def updateStatus(self,message):
        print message
        self.lblStatus.setText( message )
        self.lblStatus.repaint()
        QtCore.QCoreApplication.processEvents()
        
    @QtCore.Slot()
    def toggleLight(self):
        self.light = not(self.light)
        tc.LED( self.light )
        

def main():
    
    atexit.register( tc.cleanUp )
    app = QtGui.QApplication(sys.argv)
    tt = TransportTest()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()