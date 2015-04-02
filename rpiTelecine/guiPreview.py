# RPi Telecine live Preview widget class
#
# Widget class to show and control the live preview tab
# When visible, the live preview overlay is resized and positioned
# over the display label, to give the impression of being part of
# the application.
#
# Uses a reference to the picamera object and parent's statusbar
# overscanOffset is used to correct the position of the Pi camera preview
# overlay. There's a mismatch if the Pi has the overscan setting enabled
# in /boot/config.txt
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

from PySide import QtCore, QtGui 

from rpiTelecine.ui.livePreview import *

class LivePreview( QtGui.QWidget ):
    
    # Keep track of camera preview window size and position [x,y,w,h]
    # Preview overlays the Pi's HDMI display, so we have a placeholder label in the UI
    previewROI = [ 0.0, 0.0, 1.0, 1.0 ] # Camera preview to map into preview window
    previewCentre = [ 0.5, 0.5 ] # Centre pos of zoomed area
    previewActive = False
    previewZoom = 1.0
    # Offset used for preview overlay - needed to adjust for overscan settings
    overscanOffset = (2,2)
    
    exposureUpdated = QtCore.Signal()
    exposureSaveDefault = QtCore.Signal()
    
    def __init__(self,camera,overscanOffset=(2,2),parent=None):
        super(LivePreview, self).__init__(parent)
        self.camera = camera
        self.overscanOffset = overscanOffset
        self.zoomAspect = 1.333
        self.saved_camera_zoom = self.camera.zoom
        self.ui = Ui_livePreviewForm()
        self.ui.setupUi(self)
        self.statusbar = parent.ui.statusbar
        self.ui.sliderPreviewZoom.valueChanged.connect( self.changePreviewZoom )
        self.ui.btnPreviewL.clicked.connect(self.previewLeft)
        self.ui.btnPreviewR.clicked.connect(self.previewRight)
        self.ui.btnPreviewU.clicked.connect(self.previewUp)
        self.ui.btnPreviewD.clicked.connect(self.previewDown)
        self.ui.btnAutoExpose.clicked.connect(self.autoExposure)
        self.ui.btnPreviewSave.clicked.connect(self.exposureSaveDefault.emit)
        self.ui.cmbAWBMode.insertItem(0,'auto')
        for awbMode in sorted(camera.AWB_MODES.keys()):
            if awbMode not in ['off','auto']:
                self.ui.cmbAWBMode.insertItem(99,awbMode)
        
    def resizeEvent(self, event):
        # Keep track of preview area size and position
        self.updatePreview()

    def updatePreview(self):
        if self.previewActive:
            # Change camera preview size
            if self.camera.preview==None:
                self.camera.start_preview()
            self.camera.preview.fullscreen = False
            previewPos = self.ui.lblPreview.mapToGlobal(QtCore.QPoint(0,0))
            # Calculate w&h and position in centre of Preview area, keeping aspect ratio
            x = previewPos.x()
            y = previewPos.y()
            w = self.ui.lblPreview.width()
            h = self.ui.lblPreview.height()
            neww = int(h*self.zoomAspect)
            newh = int(w/self.zoomAspect)
            pw = neww if newh>h else w
            ph = newh if neww>w else h
            px = x+(w/2)-(pw/2)
            py = y+(h/2)-(ph/2)
            preview = [ x+self.overscanOffset[0], y+self.overscanOffset[1], w, h ]
            self.statusbar.showMessage( 'Position:{0},{1} Size:{2}x{3}'.format(*preview),750 )
            self.camera.preview.window = preview
            self.updateZoom()
        else:
            if self.camera.preview!=None:
                self.camera.stop_preview()
                
    def moveEvent(self, event):
        # Keep track of preview area position
        self.updatePreview()
        super(LivePreview, self).moveEvent(event)

    def activatePreview(self, p=True):
        if p:
            print('Live preview activated')
            self.saved_camera_zoom = self.camera.zoom
            self.previewActive = True
            x,y,w,h = self.camera._default_crop
            self.zoomAspect = float(h) / float(w)
            self.updatePreview()
            self.previewDisplayExposure()
        elif self.previewActive:
            print('Live preview off')
            self.previewActive = False
            self.updatePreview()
            self.camera.zoom = self.saved_camera_zoom


    def changePreviewZoom(self,zoom):
        zoom = round( zoom/10.0, 1 )
        self.previewZoom = zoom
        self.updateZoom()

    def updateZoom(self):
        # Check zoom position based on magnification/size
        x,y = self.previewCentre
        x = x if x>=0.0 else 0.0
        x = x if x<=1.0 else 1.0
        y = y if y>=0.0 else 0.0
        y = y if y<=1.0 else 1.0
        self.previewCentre = [x,y]
        wh = 1.0/self.previewZoom
        cx = self.previewCentre[0]-(wh/2.0)
        cx = round(cx,2) if cx>=0.0 else 0.0
        cy = self.previewCentre[1]-(wh/2.0)
        cy = round(cy,2) if cy>=0.0 else 0.0
        wh = round(wh,2)
        zoom = [cx,cy,wh,wh]
        self.camera.zoom = [cx,cy,wh,wh]
        #self.updatePreview()
        self.statusbar.showMessage( 'Zoom: {0},{1} {2}x{3}'.format(*zoom),1000 )

    def previewLeft(self):
        self.previewCentre[0] -= 0.1
        self.updateZoom()

    def previewRight(self):
        self.previewCentre[0] += 0.1
        self.updateZoom()

    def previewUp(self):
        self.previewCentre[1] -= 0.1
        self.updateZoom()

    def previewDown(self):
        self.previewCentre[1] += 0.1
        self.updateZoom()
        
    def previewDisplayExposure(self):
        g = self.camera.awb_gains
        text = '<b>Shutter:</b><br>{:d}<br> <br><b>AWB gain:</b><br>r:{:1.3f}<br>b:{:1.3f}'.format(self.camera.exposure_speed,float(g[0]),float(g[1]))
        self.ui.lblExpInfo.setText(text)
        
    def autoExposure(self):
        self.camera.exposure_mode = 'auto'
        self.camera.awb_mode = self.ui.cmbAWBMode.currentText()
        self.camera.shutter_speed = 0
        self.ui.lblExpInfo.setText('<b>Running<br>auto<br>exposure</b>')
        QtCore.QCoreApplication.processEvents() # Make sure message is displayed
        QtCore.QThread.sleep(3)
        self.camera.shutter_speed = self.camera.exposure_speed
        g = self.camera.awb_gains
        self.camera.exposure_mode = 'off'
        self.camera.awb_mode = 'off'
        self.camera.awb_gains = g
        self.previewDisplayExposure()
        # emit exposure updated 
        self.exposureUpdated.emit()