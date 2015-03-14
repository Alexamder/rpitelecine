# RPi Telecine job setuo widget class
#
# Widget class to setup a telecine job
#
# Shows a zoomable preview of the full captured frame with crop lines and
# detected perforation.
#
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

import os
import numpy as np
import time

from PySide import QtCore, QtGui 

from rpiTelecine.ui.setupJob import *
import rpiTelecine.guiCommon as guiCommon

class CameraPreviewUpdater(QtCore.QThread):
    # Thread to update camera preview image
    # It will take a picture immediate on a call to takePicture
    # or after 1/2 second after calling using updatePicture

    pictureReady = QtCore.Signal(np.ndarray)
    timer = QtCore.QTimer()
    mutex = QtCore.QMutex()
    delay = 500
    exiting = False
    ready = False
    active = True

    def __init__(self,camera,parent = None):
        super(CameraPreviewUpdater, self).__init__(parent)
        self.camera=camera
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.takePicture)

    def takePicture(self):
        self.ready=True
        
    def updatePicture(self):
        self.ready = False
        self.timer.stop()
        self.timer.start(self.delay)

    def run(self):
        global previewImg
        while not self.exiting:
            if self.active and self.ready:
                print "Taking picture"
                self.ready = False
                img = self.camera.take_picture()
                self.mutex.lock()
                previewImg = img
                self.mutex.unlock()
                print "Picture taken"
                self.pictureReady.emit(img)
            else:
                # Needed to keep UI responsive
                QtCore.QThread.msleep(50)

    def pause(self, p=True):
        self.active = not(p)

    def stop(self):
        self.mutex.lock()
        self.exiting = True
        self.mutex.unlock()
        self.wait()

class SetupJob( QtGui.QWidget ):

    # Signals
    filmTypeChanged = QtCore.Signal(str) # Emits new film type
    jobNameChanged = QtCore.Signal(str) # Emits a change of job name
    outputDirectoryChanged = QtCore.Signal(str) # Emits new output dir name

    scaleFactor = 1.15

    def __init__(self,camera,tc,pf,parent=None):
        super(SetupJob, self).__init__(parent)

        self.camera = camera

        self.filmType = 'super8'
        self.pf = pf
        self.tc = tc

        self.ui = Ui_SetupJobForm()
        self.ui.setupUi(self)
        self.statusbar = parent.ui.statusbar

        # Set up preview
        self.scene = QtGui.QGraphicsScene()
        self.scene.setBackgroundBrush(QtGui.QColor(64,64,64))
        self.view  = QtGui.QGraphicsView(self.scene, self)
        # Redirect wheelEvent to allow zooming with mousewheel
        self.view.wheelEvent = self.viewWheelEvent 
        # Mouse dragging to move preview
        self.view.setDragMode(QtGui.QGraphicsView.ScrollHandDrag)

        w,h = self.camera.resolution

        self.previewQimg = QtGui.QImage(w, h, QtGui.QImage.Format_RGB32)
        self.previewQimg.fill(QtGui.QColor(50,50,50))

        self.view.setSceneRect(0, 0, w, h)
        self.ui.layoutPreview.insertWidget(0,self.view)
        self.ui.btnOne2one.clicked.connect( self.viewOne2one )

        self.ui.btnZoomIn.clicked.connect( self.zoomIn )
        self.ui.btnZoomOut.clicked.connect( self.zoomOut )
        self.ui.btnFit.clicked.connect( self.fitToWindow )

        self.setupViewScene()

        # Job Setup tab
        self.ui.btnChangeJobName.clicked.connect(self.changeJobName)
        self.ui.btnChooseDir.clicked.connect(self.chooseOutputDirectory)
        self.ui.btnChangeFilm.clicked.connect(self.changeFilmType)
        self.ui.spinShutter.valueChanged.connect( self.updateCameraShutterSpeed )
        self.ui.spinGainR.valueChanged.connect( self.updateCameraGains )
        self.ui.spinGainB.valueChanged.connect( self.updateCameraGains )

        # Preview updater thread
        self.previewUpdater = CameraPreviewUpdater(self.camera,parent)
        self.previewUpdater.pictureReady.connect(self.updatePicture)
        self.previewUpdater.start()
        self.ui.btnStop.clicked.connect( self.previewUpdater.updatePicture )

    def viewWheelEvent(self, event):
        # Use mouse for zooming the preview image and limit extents
        self.view.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        if event.delta() > 0:
            self.zoomIn()
        else:
            self.zoomOut()

    def close(self):
        # Need to gracefully stop the preview update
        print "Exiting preview"
        self.previewUpdater.stop()

    def pauseUpdating(self,p=True):
        self.previewUpdater.pause(p)

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
                    self.jobNameChanged.emit(jobName)
                else:
                    # Invalid job name
                    ok = False
                    message = "Invalid characters. Try again.<br>Enter job name."

    def chooseOutputDirectory(self):
        # Sets the output directory
        d = os.path.dirname(self.ui.lblProjectDir.text())
        d = d if os.path.exists(d) else os.getcwd()
        flags = QtGui.QFileDialog.DontResolveSymlinks | QtGui.QFileDialog.ShowDirsOnly
        d = QtGui.QFileDialog.getExistingDirectory(self, "Open Directory", d, flags)
        if os.path.exists(d):
            self.ui.lblProjectDir.setText(d)
            self.outputDirectoryChanged.emit(d)

    def changeFilmType(self):
        # Warning message before changing film
        f = ('Standard 8','Super 8') if self.filmType=='std8' else ('Super 8','Standard 8')
        message = 'Are you sure you want to change<br>from <b>{}</b> to <b>{}</b> film?<br>Some settings will be reset.'.format(*f)
        reply = QtGui.QMessageBox.question(self, 'Message',message, QtGui.QMessageBox.Yes | 
            QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.Yes:
            f = 'super8' if self.filmType=='std8' else 'std8'
            self.setFilmType(f,forceChange=True)

    def setFilmType(self, f, forceChange=False):
        # Sets up the film type - resets the perforation detection
        if forceChange or f != self.filmType:
            fname = 'Standard 8' if f=='std8' else 'Super 8'
            self.ui.lblFilmType.setText(fname)
            self.filmType = f
            self.pf.init( f, imageSize=self.camera.resolution, expectedSize=(0,0), cx=0 )
            self.filmTypeChanged.emit(f)

    def updateCameraShutterSpeed(self):
        # Called when using the spinbox
        self.camera.shutter_speed = int(self.ui.spinShutter.value())
        self.previewUpdater.updatePicture()

    def updateCameraGains(self):
        awb_gains = ( float(self.ui.spinGainR.value()),
                      float(self.ui.spinGainB.value()) )
        self.camera.awb_gains = awb_gains
        self.previewUpdater.updatePicture()

    def setCameraExposure(self,shutter,gain_r,gain_b):
        self.camera.setup_cam( shutter = int(shutter), 
                               awb_gains = ( float(gain_r),float(gain_b) ) )
        self.ui.spinShutter.setValue(self.camera.shutter_speed)
        self.ui.spinGainR.setValue(float(gain_r))
        self.ui.spinGainB.setValue(float(gain_b))

    def updateExposureControls(self):
        self.ui.spinShutter.setValue(self.camera.shutter_speed)
        gain_r, gain_b = self.camera.awb_gains           
        self.ui.spinGainR.setValue(float(gain_r))
        self.ui.spinGainB.setValue(float(gain_b))

    def jobName(self):
        return self.ui.lblJobName.text()

    def setJobName(self, jobName):
        self.ui.lblJobName.setText( jobName )

    def jobDir(self):
        return self.ui.lblJobDir.text()

    def setJobDir(self, jobDir):
        # Update the job dir label
        self.ui.lblJobDir.setText( jobDir )

    def projectDir(self):
        return self.ui.lblProjectDir.text()

    def setProjectDir(self, projectDir):
        # Update the job dir label
        self.ui.lblProjectDir.setText( projectDir )

    def setupViewScene(self):
        # Set up the various objects on the view
        # Pixmap of preview image
        self.pixmap = self.scene.addPixmap( QtGui.QPixmap.fromImage(self.previewQimg) )
        # Set an initial scale of 50%
        self.view.scale(0.5,0.5)
        self.view.centerOn(self.pixmap)
        # Crop rectangle
        pen = QtGui.QPen(QtCore.Qt.green, 11, QtCore.Qt.SolidLine)
        self.cropRect = self.scene.addRect(400,350,1600,1200,pen)
        self.cropRect.setOpacity(0.6)
        # Perforation rectangle
        pen.setColor(QtCore.Qt.red)
        brush = QtGui.QBrush(QtGui.QColor(255, 0, 0,64))
        self.perfRect = self.scene.addRect(150,800,250,300,pen,brush)
        self.perfRect.setOpacity(0.6)
        # ROI rectangle
        pen.setColor(QtCore.Qt.yellow)
        self.ROIrect = self.scene.addRect(130,500,290,922,pen)
        self.ROIrect.setOpacity(0.6)
        # Area for histogram calculation
        pen = QtGui.QPen(QtCore.Qt.green, 7, QtCore.Qt.DotLine)
        self.histRect = self.scene.addRect(500,450,1400,1000,pen)
        self.histRect.setOpacity(0.4)


    def updatePicture(self,img):
        # Updates the preview image and histogram
        print("Updating picture {}".format(id(img)))
        self.previewQimg = guiCommon.makeQimage(img)
        hist = guiCommon.makeHistImage(img)
        self.histqi = guiCommon.makeQimage(hist)
        #self.imageView.setImage( self.previewQimg )
        self.ui.lblHistogram.setPixmap(QtGui.QPixmap.fromImage(self.histqi))
        self.pixmap.setPixmap( QtGui.QPixmap.fromImage(self.previewQimg) )

    def viewOne2one(self):
        # Set the view to 100%
        self.view.setTransform(QtGui.QTransform.fromScale(1.0, 1.0))

    def fitToWindow(self):
        # Resize to fit image in view window
        self.view.fitInView(self.pixmap, QtCore.Qt.KeepAspectRatio)

    def zoomIn(self):
        # Use mouse for zooming the preview image and limit extents
        if self.view.transform().m11() < 4.0: 
            self.view.scale(self.scaleFactor, self.scaleFactor);

    def zoomOut(self):
        if self.view.transform().m11() > 0.1:
            #Zoom out
            self.view.scale(1.0 / self.scaleFactor, 1.0 / self.scaleFactor)
