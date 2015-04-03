#!/usr/bin/env python

# RPi Telecine PySide controller test program
#
# Simple GUI to test the functions of the RPi Telecine control PCB
#
# It has a bunch of buttons for running the motors, switching the LED on and
# off, for testing the SLR shutter release.
#
# It can also be used to fast rewind the film
#
# Make sure the correct declaration of the tc object is uncommented below -
# If you use stepper motors for the takeup spools, then the parameter 
# 'useFourStepper' has to be set to True.
#
# The GuiTelecineControl object uses a PySide QThread for stepping the motors 
# in the background, to prevent the UI from blocking while the film is 
# moving. It also emits signals while the film is moving, so that an activity
# spinner can be animated.
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


import sys
import atexit

from PySide import QtCore, QtGui 

from rpiTelecine.guiControl import GuiTelecineControl

# Use this line if using DC motors for the film spools
tc = GuiTelecineControl()
# Use this line if using stepper motors for the film spools
#tc = GuiTelecineControl(useFourStepper=True)

frameSteps = 300

class TransportTest(QtGui.QWidget):

    def __init__(self):
        super( TransportTest, self).__init__()
        self.initUI()
        tc.setTakeUpCount( frameSteps * 3 )
        self.connectSignalsSlots()
        self.setGeometry(300, 300, 300, 400)
        self.setWindowTitle("Test rpiTelecine Controller")
        self.show()

    def connectSignalsSlots(self):
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
        self.lblStatus = QtGui.QLabel('Paused')
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Foreground,QtCore.Qt.red)
        self.lblStatus.setPalette(palette)
        self.lblSpinner = QtGui.QLabel("|")
        font = QtGui.QFont('',14,QtGui.QFont.Bold)
        self.lblSpinner.setFont(font)
        self.lblTitle = QtGui.QLabel('<font color="darkBlue"><b>rpiTelecine control PCB test</b></font>')
        hbox = QtGui.QHBoxLayout()
        hbox2 = QtGui.QHBoxLayout()
        hbox3 = QtGui.QHBoxLayout()
        hbox4 = QtGui.QHBoxLayout()
        hbox5 = QtGui.QHBoxLayout()
        hbox6 = QtGui.QHBoxLayout()
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
        hbox5.addWidget(self.btnRewind)
        hbox5.addWidget(self.btnStopWind)
        hbox5.addWidget(self.btnWindOn)
        hbox6.addWidget(self.lblSpinner)
        hbox6.addStretch(0)
        hbox6.addWidget(self.lblStatus)
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.lblTitle)
        vbox.addLayout(hbox6)
        vbox.addStretch(1)
        vbox.addWidget( QtGui.QLabel('Shutter Release') )
        vbox.addLayout(hbox3)
        vbox.addStretch(1)
        vbox.addWidget( QtGui.QLabel('LED Lamp') )
        vbox.addLayout(hbox2)
        vbox.addStretch(1)
        vbox.addWidget( QtGui.QLabel('Stepper motor enable/disable') )
        vbox.addLayout(hbox4)
        vbox.addStretch(1)
        vbox.addWidget( QtGui.QLabel('Film spool winding') )
        vbox.addLayout(hbox5)
        vbox.addStretch(1)
        vbox.addWidget( QtGui.QLabel('Film transport') )
        vbox.addLayout(hbox)        
        self.setLayout(vbox)

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

    light = True

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