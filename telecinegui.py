#!/usr/bin/env python

import sys
import os
import time
import atexit

from PySide.QtCore import QSettings
from PySide import QtCore, QtGui 

from rpiTelecine import ( TelecineCamera, TelecineControl, TelecinePerforation )
from rpiTelecine.ui.telecineui import *
from rpiTelecine import ( guiPreview, guiSetupJob )

camera = TelecineCamera()
pf  = TelecinePerforation()
tc  = TelecineControl()

atexit.register(camera.close)

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

    def __init__(self, parent=None):
        super(ControlMainWindow, self).__init__(parent)
        self.setWindowTitle("rpiTelecine")
        self.ui = Ui_TelecinePreview()
        self.ui.setupUi(self)

        # Job setup tab
        self.setupJob = guiSetupJob.SetupJob(camera,tc,pf,parent=self)
        self.ui.tabs.insertTab(self._setupTab,self.setupJob,'&Job setup')
        self.setupJob.jobNameChanged.connect(self.readJobSettings)

        # Capture tab

        # Live preview tab
        self.livePreview = guiPreview.LivePreview(camera, parent=self)
        self.ui.tabs.insertTab(self._previewTab,self.livePreview,'Live &Preview')

        # Preview tab
        self.ui.tabs.currentChanged.connect( self.changeTab )

        self.livePreview.exposureSaveDefault.connect(self.saveDefaultExposure)
        self.livePreview.exposureUpdated.connect(self.setupJob.updateExposureControls)

        self.ui.tabs.setCurrentIndex( self._setupTab )

        tc.light_on()

        # Load default and job settings
        self.readDefaultSettings()
        self.readJobSettings()

    def closeEvent(self, event):
        self.setupJob.close() # gracefully close the preview image thread 
        self.writeDefaultSettings()
        self.saveJobSettings()
        tc.light_off()
        event.accept()

    def changeTab(self,tab):
        self.setupJob.pauseUpdating( tab!=self._setupTab )
        self.livePreview.activatePreview( tab==self._previewTab )

    def moveEvent(self, event):
        # Force a move event on the live preview widget
        self.livePreview.moveEvent(event)
        super(ControlMainWindow, self).moveEvent(event)

    def readDefaultSettings(self):
        # Read default settings
        self.defaultSettings = QSettings(self._defaultSettingsFile, QSettings.IniFormat)
        settings = self.defaultSettings
        settings.setFallbacksEnabled(False) # only use ini file
        print "Reading settings:{}".format(self._defaultSettingsFile)

        # Window geometry
        settings.beginGroup( "mainWindow" )
        self.restoreGeometry(settings.value( "geometry", self.saveGeometry()))
        self.restoreState(settings.value( "saveState", self.saveState()))
        self.move(settings.value( "pos", self.pos()))
        self.resize(settings.value( "size", self.size()))
        if isTrue( settings.value( "maximized", self.isMaximized() ) ):
            self.showMaximized()

        # Other settings
        overscanOffset = self.livePreview.overscanOffset
        self.livePreview.overscanOffset = ( int(settings.value( "overscanOffsetx",overscanOffset[0] )),
                                            int(settings.value( "overscanOffsety",overscanOffset[1] )) )
        settings.endGroup() 
        
        settings.beginGroup( "camera" )
        self.setupJob.setCameraExposure( shutter=settings.value("shutter_speed", 2000), 
                                       gain_r=settings.value("gain_r",1.0),
                                       gain_b=settings.value("gain_b",1.0) )
        x,y,w,h = settings.value( "defaultCrop", (0,0, camera.MAX_IMAGE_RESOLUTION[0],camera.MAX_IMAGE_RESOLUTION[1]) )
        camera.camera_crop = ( int(x),int(y),int(w),int(h) )
        settings.endGroup()
        
        settings.beginGroup( "project" )
        self.setupJob.setProjectDir( settings.value('projectDir', self._defaultProjectDir ) )
        self.setupJob.setJobName( settings.value('jobName', self._defaultJobName ) )
        self.setupJob.setJobDir( settings.value('jobDir', self._defaultJobDir ) )
        self.setupJob.setFilmType( settings.value('filmType','super8') )
        settings.endGroup()

    def writeDefaultSettings(self):
        # Write default settings
        settings = self.defaultSettings

        # Window geometry
        print "Saving default settings"
        settings.beginGroup( "mainWindow" )
        settings.setValue( "geometry", self.saveGeometry() )
        settings.setValue( "saveState", self.saveState() )
        settings.setValue( "maximized", self.isMaximized() )
        if not self.isMaximized():
            settings.setValue( "pos", self.pos() )
            settings.setValue( "size", self.size() )
        settings.setValue( "overscanOffsetx", self.livePreview.overscanOffset[0] )
        settings.setValue( "overscanOffsety", self.livePreview.overscanOffset[1] )
        settings.endGroup()
        settings.beginGroup( "project" )
        settings.setValue( "projectDir", self.setupJob.projectDir() )
        settings.setValue( "jobName", self.setupJob.jobName() )
        settings.setValue( "jobDir", self.setupJob.jobDir() )
        settings.setValue( "filmType", self.setupJob.filmType )
        settings.endGroup()
        settings.beginGroup( "camera" )
        settings.setValue( "defaultCrop", camera.camera_crop )
        settings.endGroup()

    def readJobSettings(self):
        jobName = self.setupJob.jobName()
        directory = self.setupJob.projectDir()
        jobDir = os.path.join(directory,jobName)
        self.setupJob.setJobDir( jobDir ) 
        jobSettingsName = jobDir + '.ini'
        print("Reading job settings from Job INI {}".format(jobSettingsName))

        settings = QSettings(jobSettingsName, QSettings.IniFormat)
        settings.setFallbacksEnabled(False) # only use ini file
        
        settings.beginGroup( "camera" )
        default_shutter_speed = camera.shutter_speed
        default_gain_r, default_gain_b = camera.awb_gains
        shutter = int(settings.value("shutter_speed", default_shutter_speed) )
        gain_r = float(settings.value("gain_r",float(default_gain_r)))
        gain_b = float(settings.value("gain_b",float(default_gain_b)))
        self.setupJob.setCameraExposure( shutter, gain_r, gain_b )
        settings.endGroup()

        settings.beginGroup( "crop" )
        crop_offset_x = int(settings.value("crop_offset_x", 0) )
        crop_offset_y = int(settings.value("crop_offset_y", -50) )
        crop_w = int(settings.value("crop_w", 200) )
        crop_h = int(settings.value("crop_h", 200) )
        histogramArea = int(settings.value("histogram_area", 75) )
        self.setupJob.crop = ( crop_offset_x, crop_offset_y, 
                               crop_w, crop_h, histogramArea )
        settings.endGroup()

        settings.beginGroup( "perforation" )
        film_type = settings.value("film_type","super8")
        perf_cx = int(settings.value("perf_cx", 0) )
        perf_w = int(settings.value("perf_w", 0) )
        perf_h = int(settings.value("perf_h", 0) )
        self.setupJob.perforation = ( film_type, perf_cx, perf_w, perf_h )
        self.setupJob.checkEdges = int(settings.value("check_edges",0))
        self.setupJob.checkLeftEdge = isTrue(settings.value("check_left_edge",0))
        settings.endGroup()

        settings.beginGroup( "transport" )
        ave_steps_fd = float(settings.value("ave_steps_fd", 300.0) )
        ave_steps_bk = float(settings.value("ave_steps_bk", 300.0) )
        pixels_per_step = float(settings.value("pixels_per_step", 3.0) )
        self.setupJob.transport = ( ave_steps_fd, ave_steps_bk, pixels_per_step )
        settings.endGroup()

        self.setWindowTitle("rpiTelecine - {}".format(jobName))

    def saveJobSettings(self):
        # Saves job specific items to INI file in project folder
        jobName = self.setupJob.jobName()
        if jobName != '':
            directory = self.setupJob.projectDir()
            jobDir = os.path.join(directory,jobName)
            jobSettingsName = jobDir + '.ini'
            print("Saving job settings to Job INI {}".format(jobSettingsName))

            settings = QSettings(jobSettingsName, QSettings.IniFormat)

            settings.beginGroup( "camera" )
            shutter_speed = camera.shutter_speed
            gain_r, gain_b = camera.awb_gains
            settings.setValue("shutter_speed", shutter_speed)
            settings.setValue("gain_r",float(gain_r))
            settings.setValue("gain_b", float(gain_b))
            settings.endGroup()
            
            settings.beginGroup( "crop" )
            crop_offset_x, crop_offset_y, crop_w, crop_h, histogramArea = self.setupJob.crop
            settings.setValue("crop_offset_x", crop_offset_x)
            settings.setValue("crop_offset_y", crop_offset_y)
            settings.setValue("crop_w", crop_w)
            settings.setValue("crop_h", crop_h)
            settings.setValue("histogramArea", histogramArea)
            settings.endGroup()
            
            settings.beginGroup( "perforation" )
            film_type, perf_cx, perf_w, perf_h = self.setupJob.perforation
            settings.setValue("film_type", film_type)
            settings.setValue("perf_cx", perf_cx)
            settings.setValue("perf_w", perf_w)
            settings.setValue("perf_h", perf_h)
            settings.setValue("check_edges", self.setupJob.checkEdges)
            settings.setValue("check_left_edge", self.setupJob.checkLeftEdge)
            settings.endGroup()

            settings.beginGroup( "transport" )
            ave_steps_fd, ave_steps_bk, pixels_per_step = self.setupJob.transport
            settings.setValue("ave_steps_fd", ave_steps_fd)
            settings.setValue("ave_steps_bk", ave_steps_bk)
            settings.setValue("pixels_per_step", pixels_per_step)
            settings.endGroup()

    def saveDefaultExposure(self):
        # Write preview camera settings to default ini file
        settings = self.defaultSettings
        settings.beginGroup( "camera" )
        shutter_speed = camera.shutter_speed
        gain_r, gain_b = camera.awb_gains           
        settings.setValue("shutter_speed", shutter_speed)
        settings.setValue("gain_r",float(gain_r))
        settings.setValue("gain_b", float(gain_b))
        settings.endGroup()


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    previewframe = ControlMainWindow()
    previewframe.show()
    sys.exit(app.exec_())