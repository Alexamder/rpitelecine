#!/usr/bin/env python

import sys
import os
import time
import atexit

from PySide.QtCore import QSettings
from PySide import QtCore, QtGui 

from rpiTelecine import ( TelecineCamera, TelecineControl, TelecinePerforation )
from rpiTelecine.ui.telecineui import *

camera = TelecineCamera()
pf  = TelecinePerforation()
tc  = TelecineControl()

camResolution = (2592,1944)

atexit.register(camera.close)

filmType = 'super8' # or 'std8'

def isTrue(value):
    # work around issue with not being able to read booleans as booleans
    # from QSettings
    return value in ['true','True',True,1,]


class ControlMainWindow(QtGui.QMainWindow):
    
    _defaultSettingsFile = os.path.expanduser('~/.telecine.ini')
    _defaultProjectDir = os.path.expanduser('~/Telecine/')
    _defaultJobName = 'telecine'
    _defaultJobDir = os.path.expanduser('~/Telecine/telecine')

    # Numbering of the tabs
    _setupTab   = 0
    _runTab     = 1
    _previewTab = 2
    
    # Keep track of camera preview window size and position [x,y,w,h]
    # Preview overlays the Pi's HDMI display, so we have a placeholder label in the UI
    previewROI = [ 0.0, 0.0, 1.0, 1.0 ] # Camera preview to map into preview window
    previewCentre = [ 0.5, 0.5 ] # Centre pos of zoomed area
    previewActive = False
    previewZoom = 1.0
    # Offset used for preview overlay - needed to adjust for overscan settings
    overscanOffset = (2,2)

    def __init__(self, parent=None):
        super(ControlMainWindow, self).__init__(parent)
        self.ui = Ui_TelecinePreview()
        self.ui.setupUi(self)
        
        self.readDefaultSettings()
        
        # Connect signals
        # Job Setup tab
        self.ui.btnChangeJobName.clicked.connect(self.changeJobName)
        self.ui.btnChooseDir.clicked.connect(self.chooseOutputDirectory)
        self.ui.btnChangeFilm.clicked.connect(self.changeFilmType)
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
        tc.light_on()
        
    
    def closeEvent(self, e):
        self.writeDefaultSettings()
        tc.light_off()
        e.accept()
    
    def readDefaultSettings(self):
        # Read default settings
        self.defaultSettings = QSettings(self._defaultSettingsFile, QSettings.IniFormat)
        settings = self.defaultSettings
        settings.setFallbacksEnabled(False) # only use ini file
        print "Reading settings:{}".format(self._defaultSettingsFile)
        print settings.allKeys()
        # Window geometry
        settings.beginGroup( "mainWindow" )
        self.restoreGeometry(settings.value( "geometry", self.saveGeometry()))
        self.restoreState(settings.value( "saveState", self.saveState()))
        self.move(settings.value( "pos", self.pos()))
        self.resize(settings.value( "size", self.size()))
        if isTrue( settings.value( "maximized", self.isMaximized() ) ):
            self.showMaximized()
        self.overscanOffset = ( int(settings.value( "overscanOffsetx",self.overscanOffset[0] )),
                                int(settings.value( "overscanOffsety",self.overscanOffset[1] )) )
        settings.endGroup() 
        settings.beginGroup( "camera" )
        camera.setup_cam( shutter=settings.value("shutter_speed", 2000), 
                          awb_gains=( settings.value("gain_r",1.0), 
                                      settings.value("gain_b",1.0) ) )
        settings.endGroup()
        settings.beginGroup( "project" )
        self.ui.lblProjectDir.setText( settings.value('projectDir', self._defaultProjectDir ) )
        self.ui.lblJobName.setText( settings.value('jobName', self._defaultJobName ) )
        self.ui.lblJobDir.setText( settings.value('jobDir', self._defaultJobDir ) )
        settings.endGroup()
        
    def writeDefaultSettings(self):
        # Write default settings
        settings = self.defaultSettings

        # Window geometry
        print "Saving settings"
        settings.beginGroup( "mainWindow" )
        settings.setValue( "geometry", self.saveGeometry() )
        settings.setValue( "saveState", self.saveState() )
        settings.setValue( "maximized", self.isMaximized() )
        if not self.isMaximized():
            settings.setValue( "pos", self.pos() )
            settings.setValue( "size", self.size() )
        settings.setValue( "overscanOffsetx", self.overscanOffset[0] )
        settings.setValue( "overscanOffsety", self.overscanOffset[1] )
        settings.endGroup()
        settings.beginGroup( "project" )
        settings.setValue( "projectDir", self.ui.lblProjectDir.text() )
        settings.setValue( "jobName", self.ui.lblJobName.text() )
        settings.setValue( "jobDir", self.ui.lblJobDir.text() )
        settings.endGroup()
        

    def changeJobName(self):
        # Uses input dialog to get job name from user
        ok = False
        message = "Enter job name."
        while not ok:
            text, result = QtGui.QInputDialog.getText(self, "Change Job Name", message)
            ok = True
            if result:
                # Sanitise job name as we'll be using it as a folder name
                delchars = ''.join(c for c in map(chr, range(256)) if not c.isalnum())
                jobName = text.encode('ascii','ignore')
                jobName = jobName.translate(None,delchars)
                if jobName:
                    self.ui.lblJobName.setText(jobName)
                    self.updateJobFolder()
                else:
                    # Invalid job name
                    ok = False
                    message = "Invalid characters. Try again.<br>Enter job name."

    def updateJobFolder(self):
        # Takes the current project folder and job name and creates the 
        # output folder
        jobName = self.ui.lblJobName.text()
        directory = self.ui.lblProjectDir.text()
        jobDir = os.path.join(directory,jobName)
        print("Updating job folder: Job Name: {} Project Dir: {} Job Dir {}".format(jobName,directory,jobDir))
        self.ui.lblJobDir.setText( jobDir )

    def chooseOutputDirectory(self):
        # Sets the output directory
        d = os.path.dirname(self.ui.lblProjectDir.text())
        d = d if os.path.exists(d) else os.getcwd()
        flags = QtGui.QFileDialog.DontResolveSymlinks | QtGui.QFileDialog.ShowDirsOnly
 	d = QtGui.QFileDialog.getExistingDirectory(self, "Open Directory", d, flags)
        if os.path.exists(d):
            self.ui.lblProjectDir.setText(d)
            self.updateJobFolder()
    
    def changeFilmType(self):
        # Warning message before changing film
        global filmType
        f = ('Standard 8','Super 8') if filmType=='std8' else ('Super 8','Standard 8')
        message = 'Are you sure you want to change<br>from <b>{}</b> to <b>{}</b> film?<br>Some settings will be reset.'.format(*f)
        reply = QtGui.QMessageBox.question(self, 'Message',message, QtGui.QMessageBox.Yes | 
            QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.Yes:
	    filmType = 'super8' if filmType=='std8' else 'std8'
            self.ui.lblFilmType.setText(f[1])

    def updatePreview(self):
        if self.previewActive:
            # Change camera preview size
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
            preview = [ x+self.overscanOffset[0], y+self.overscanOffset[1], w, h ]
            self.ui.statusbar.showMessage( 'Position:{0},{1} Size:{2}x{3}'.format(*preview),750 )
            camera.preview.window = preview
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
            print('Preview activated')
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