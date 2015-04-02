#!/usr/bin/env python

import sys
import os
import time
import atexit

from PySide.QtCore import QSettings
from PySide import QtCore, QtGui 

from rpiTelecine import ( StepperMotor,ReelMotor,LedControl )

import wiringpi2 as wiringpi

frameSteps = 314

FORWARD = True
BACKWARD = False

class Stepper(QtCore.QObject):
    # Designed to run in a thread
    
    finished = QtCore.Signal()
    isRunning = QtCore.Signal()
    
    steps = 0
    exiting = False
    quiet = False # suppress signals while true
    
    updateCount =150
    tensionCount = 50
    takeUpCount = frameSteps * 4
    
    def __init__(self,m1,m2,m3,m4):
        super( Stepper, self ).__init__()
        self.m1 = m1
        self.m2 = m2
        self.m3 = m3
        self.m4 = m4
        
        
        
    @QtCore.Slot()
    def runner(self):
        m1 = self.m1.step   # Speed up loop a bit by not evaluating dots
        m2 = self.m2.step
        fourStepper = ( type(m3) == type(m4) == StepperMotor )
        
        if self.m3 != None:
            m3 = self.m3.step
            m4 = self.m4.step
        updateCounter = self.update
        tensionCounter = self.tensionCount
        takeUpCounterFwd = self.takeUpCount
        takeUpCounterBack = self.takeUpCount
        
        while not self.exiting:
            while self.steps > 0:
                self.steps -= 1
                if self.direction:
                    # FORWARD
                    print 'fwd ',
                    time.sleep(0.25)
                else:
                    # BACKWARD
                    print 'back ',
                    time.sleep(0.25)
                self.updateCounter -= 1
                if updateCounter < 1:
                    updateCounter = self.updateCount
                    if not self.quiet:
                        self.isRunning.emit()
            if not self.quiet:
                self.finished.emit()
            time.sleep(0.1)
    
    @QtCore.Slot(bool)
    def setQuietmode(quiet = True)
        self.quiet = quiet

    @QtCore.Slot()
    def stopStepping(self):
        self.steps = 0

    @QtCore.Slot(int)
    def stepForward(self, steps):
        if self.direction == BACKWARD:
            self.direction = FORWARD
        self.steps += steps

    @QtCore.Slot(int)
    def stepBackward(self, steps):
        self.mutex.lock()
        if self.direction == FORWARD:
            self.direction = BACKWARD
            self.steps = 0
        self.steps += steps
        self.mutex.unlock()
    
    @QtCore.Slot()
    def close(self):
        self.exiting = True
    
    

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
    
    runCount = 150
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
        self.fourStepper = useFourStepper
        self.m1 = StepperMotor(pin['m1Step'],pin['m1Dir'],pin['m1Enable'])
        self.m2 = StepperMotor(pin['m2Step'],pin['m2Dir'],pin['m2Enable'])
        if self.fourStepper:
            self.m3 = StepperMotor(pin['m3Step'],pin['m3Dir'],pin['m34Enable'])
            self.m4 = StepperMotor(pin['m4Step'],pin['m4Dir'],pin['m34Enable'])
        else:
            # DC motors for takeup reels
            self.m3 = ReelMotor(pin['reel1'])
            self.m4 = ReelMotor(pin['reel2'])
        self.stepperWorker = Stepper(m1,m2,m3,m4)
        self.stepperWorker.moveToThread(self.stepperThread)
        self.stepperThread.started.connect( self.stepperWorker.runner )
        
        
        # LED control
        self.led = LedControl(pin['led'])
        self.led.on()
        # Shutter release
        #self.shutterRelease = ShutterRelease(pin['focus'], pin['shutter'])

        # Direction of film travel - 
        # Forward: True = m1 to m2 False = m2 to m1
        self.direction = True

    def cleanUp(self):
        self.led.off()
        # De-energise steppers
        self.m1.off()
        self.m2.off()
        if self.fourStepper:
            self.m3.off()

    
    
    
    @QtCore.Slot(int)
    def stepForward( self,steps=314 ):
        m1step = self.m1.step   # Speed up loop a bit by not evaluating dots
        m2step = self.m2.step
        #if not self.direction:
        #    self.tc.change_direction( True )
        while steps>1:
            steps -= 1
            self.runCounter -= 1
            if self.runCounter <= 0:
                self.runCounter = self.runCount
                self.runSig.emit()
                QtCore.QCoreApplication.processEvents()
            self.takeUpCounterFwd -= 1
            if self.takeUpCounterFwd<=0:
                self.reel2.pulse()
                self.takeUpCounterFwd=self.takeUpSteps
            if self.tensionCounter>0:
                # Push film one step
                m1step()
                self.tensionCounter -= 1
            else:
                # Skip pushing
                self.tensionCounter = self.tensionSteps
            # Pull film one step
            m2step()


tc = GuiTC()

class TransportTest(QtGui.QWidget):
    
    def __init__(self):
        super( TransportTest, self).__init__()
        self.initUI()
        
        sw = tc.stepperWorker
        self.btnFwd.clicked.connect( lambda: sw.stepForward(frameSteps) )
        self.btnFFwd.clicked.connect( lambda: sw.stepForward(frameSteps*18) )
        self.btnBack.clicked.connect( lambda: sw.stepBackward(frameSteps) )
        self.btnFBack.clicked.connect( lambda: sw.stepBackward(frameSteps*18) )
        tc.runSig.connect(self.updateSpinner)
 

    def initUI(self):
        self.btnFwd = QtGui.QPushButton(">")
        self.btnBack = QtGui.QPushButton("<")
        self.btnFFwd = QtGui.QPushButton(">>")
        self.btnFBack = QtGui.QPushButton("<<")
        self.btnStop = QtGui.QPushButton("Stop")
        self.lblCounter = QtGui.QLabel("Frames")
        self.lblSpinner = QtGui.QLabel("|")
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.btnFBack)
        hbox.addWidget(self.btnBack)
        hbox.addWidget(self.btnStop)
        hbox.addWidget(self.btnFwd)
        hbox.addWidget(self.btnFFwd)
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.lblCounter)
        vbox.addWidget(self.lblSpinner)
        vbox.addStretch(1)
        vbox.addLayout(hbox)
        self.setLayout(vbox)
        self.setGeometry(300, 300, 300, 150)
        self.setWindowTitle("Test Transport")
        self.show()

    spin = 0
    spinChars = '|\-/'
    
    def updateSpinner(self):
        self.lblSpinner.setText( self.spinChars[self.spin] )
        self.spin = (self.spin + 1) % len(self.spinChars)
        self.lblSpinner.repaint()

def main():
    
    atexit.register( tc.cleanUp )
    app = QtGui.QApplication(sys.argv)
    tt = TransportTest()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()