#!/usr/bin/env python

import sys
import time
import atexit
from PySide import QtCore, QtGui 
import picamera

from rpiTelecine.ui.telecineui import *

camResolution = (2592,1944)

camera = picamera.PiCamera()
atexit.register(camera.close)

# Basic settings
camera.vflip = True
camera.sensor_mode = 2
camera.framerate = 15    # Needed for full resolution preview
camera.resolution = camResolution

#camera.shutter_speed = 1000
camera.iso = 100
#camera.analog_gain = 1.0
#camera.digital_gain = 1.0
camera.exposure_mode = 'off'
camera.awb_mode = 'off'
camera.awb_gain = (1.2,1.2)

print camera.EXPOSURE_MODES
print camera.AWB_MODES

# Offset used for preview overlay - needed to adjust for overscan settings
overscanOffset = (2,2)

class ControlMainWindow(QtGui.QMainWindow):

    # Numbering of the tabs
    _setupTab   = 0
    _runTab     = 1
    _previewTab = 2
    
    # Keep track of camera preview window size and position [x,y,w,h]
    # Preview overlays the Pi's HDMI display, so we have a placeholder label in the UI
    preview = [ 0,0,0,0 ] # preview window in UI 
    previewROI = [ 0.0, 0.0, 1.0, 1.0 ] # Camera preview to map into preview window
    previewCentre = [ 0.5, 0.5 ] # Centre pos of zoomed area
    previewActive = False
    previewZoom = 1.0
    
    def __init__(self, parent=None):
        super(ControlMainWindow, self).__init__(parent)
        self.ui = Ui_TelecinePreview()
        self.ui.setupUi(self)
        
        # Connect signals
        # Preview tab
        self.ui.tabs.currentChanged.connect( self.changeTab )
        self.ui.sliderPreviewZoom.valueChanged.connect( self.changePreviewZoom )
        self.ui.btnPreviewL.clicked.connect(self.previewLeft)
        self.ui.btnPreviewR.clicked.connect(self.previewRight)
        self.ui.btnPreviewU.clicked.connect(self.previewUp)
        self.ui.btnPreviewD.clicked.connect(self.previewDown)
        self.ui.btnAutoExpose.clicked.connect(self.autoExposure)
        self.ui.cmbAWBMode.insertItem(0,'auto')
        for awbMode in sorted(camera.AWB_MODES.keys()):
            if awbMode not in ['off','auto']:
                self.ui.cmbAWBMode.insertItem(99,awbMode)

    def updatePreview(self):
        if self.previewActive:
            # Change camera preview size
            self.ui.statusbar.showMessage( 'Position:{0},{1} Size:{2}x{3}'.format(*self.preview),750 )
            if camera.preview==None:
                camera.start_preview()
            camera.preview.fullscreen = False
            previewPos = self.ui.lblPreview.mapToGlobal(QtCore.QPoint(0,0))
            # Calculate w&h and position in centre of Preview area, keeping 4:3 aspect ratio
            x = previewPos.x()
            y = previewPos.y()
            w = self.ui.lblPreview.width()
            h = self.ui.lblPreview.height()
            neww = int(h*1.333)
            newh = int(w/1.333)
            pw = neww if newh>h else w
            ph = newh if neww>w else h
            px = x+(w/2)-(pw/2)
            py = y+(h/2)-(ph/2)
            self.preview = [ x+overscanOffset[0], y+overscanOffset[1], w, h ]
            camera.preview.window = self.preview
        else:
            if camera.preview!=None:
                camera.stop_preview()

    def resizeEvent(self, event):
        # Keep track of preview area size and position
        self.updatePreview()
        super(ControlMainWindow, self).resizeEvent(event)

    def moveEvent(self, event):
        # Keep track of preview area position
        self.updatePreview()
        super(ControlMainWindow, self).moveEvent(event)

    def changeTab(self,tab):
        if tab==self._previewTab:
            # Activate preview here
            self.ui.statusbar.showMessage( 'Preview activated. Position:{0},{1} Size:{2}x{3}'.format(*self.preview),2000 )
            print('Preview activated')
            print('Position: {0},{1} Size: {2}x{3}'.format( *self.preview ) )
            self.previewActive = True
        else:
            print('Preview off')
            self.previewActive = False
        self.updatePreview()

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
        camera.zoom = [cx,cy,wh,wh]
        #self.updatePreview()
        self.ui.statusbar.showMessage( 'Zoom: {0},{1} {2}x{3}'.format(*zoom),1000 )

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
        
    def autoExposure(self):
        camera.exposure_mode = 'auto'
        camera.awb_mode = self.ui.cmbAWBMode.currentText()
        camera.shutter_speed = 0
        self.ui.lblExpInfo.setText('<b>Running<br>auto<br>exposure</b>')
        QtCore.QCoreApplication.processEvents() # Make sure message is displayed
        QtCore.QThread.usleep(100)
        for tab in [self._setupTab,self._runTab]:
            self.ui.tabs.setTabEnabled(tab,False)
        QtCore.QThread.sleep(3)
        for tab in [self._setupTab,self._runTab]:
            self.ui.tabs.setTabEnabled(tab,True)
        camera.shutter_speed = camera.exposure_speed
        g = camera.awb_gains
        camera.exposure_mode = 'off'
        camera.awb_mode = 'off'
        camera.awb_gains = g
        text = '<b>Shutter:</b><br>{:d}<br><b>AWB gain:</b><br>r:{:1.3f}<br>b:{:1.3f}'.format(camera.exposure_speed,float(g[0]),float(g[1]))
        self.ui.lblExpInfo.setText(text)
        print('autoExposure finished')
        
            
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    previewframe = ControlMainWindow()
    previewframe.show()
    sys.exit(app.exec_())