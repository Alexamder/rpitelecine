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

from __future__ import division
from timer import Timer
import os
import numpy as np
import time
import cv2
from PySide import QtCore, QtGui 

from rpiTelecine.ui.setupJob import *
import rpiTelecine.guiCommon as guiCommon

class CameraPreviewUpdater(QtCore.QThread):
    # Thread to update camera preview image
    # It will take a picture immediate on a call to takePicture
    # or after 3/4 second after calling updatePicture
    # to allow for updates in the UI before taking picture
    pictureReady = QtCore.Signal(np.ndarray)
    timer = QtCore.QTimer()
    mutex = QtCore.QMutex()
    delay = 750
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
        while not self.exiting:
            if self.active and self.ready:
                print "Taking picture"
                self.ready = False
                img = self.camera.take_picture()
                self.mutex.lock()
                print("Picture shape: {}".format(img.shape))
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

#*******************************************************************************

'''
Class for the preview image - showing camera image, crop lines, etc.
Elements we show are: Current frame image from camera, optional overlay
showing clipped pixel values; crop rectangle in green; detected perforation 
in red; perforation detection area in yellow; offset between detected 
perforation and centre of detection area used for correcting transport to
the next frame
'''

class PreviewScene( QtGui.QGraphicsScene ):


    histRectChanged = QtCore.Signal()
    doubleClicked = QtCore.Signal(tuple)

    def __init__(self,parent=None):
        super(PreviewScene,self).__init__(parent)

        self.setBackgroundBrush(QtGui.QColor(64,64,64))

        # Set up the various objects on the view
        # Pixmap of preview image
        print "Adding pixmap"
        self.pixmap = self.addPixmap(QtGui.QPixmap(400,300))
        self.pixmap.setPos( 0,0 )
        
        # Pixmap for clipped image
        self.clippedPixmap = self.addPixmap(QtGui.QPixmap(10,10))
        self.clippedPixmap.setOpacity(0.75)
        self.clippedPixmap.setVisible(False)

        # Crop rectangle
        pen = QtGui.QPen(QtCore.Qt.green, 11, QtCore.Qt.SolidLine)
        self.cropRect = self.addRect(0,0,100,100,pen)

        # Perforation rectangle
        pen.setColor(QtCore.Qt.red)
        self.perfRect = self.addRect(0,0,110,110,pen)

        # ROI rectangle
        pen.setColor(QtCore.Qt.yellow)
        self.ROIrect = self.addRect(0,0,50,50,pen)

        # Area for histogram calculation
        pen = QtGui.QPen(QtCore.Qt.green, 5, QtCore.Qt.DotLine)
        self.histRect = self.addRect(0,0,60,60,pen)
        self.histRectProportion = 0.75

        # Perforation offset line
        pen = QtGui.QPen(QtCore.Qt.darkBlue, 5, QtCore.Qt.DotLine)
        self.vDiffLine = self.addLine(0,0,0,100,pen)

        # Show or hide the guideline items
        self.guidelineList = ( self.cropRect,
                               self.histRect,
                               self.perfRect,
                               self.ROIrect,
                               self.vDiffLine )
        self.guidelinesVisible = False
        # We can dim the guidelines if we haven't detected a perforation
        self.guidelinesBright = True
        # Offset from centre of perforation to top left of crop rectangle

        self.perforationCentre = QtCore.QPoint(0,0)
        self.cropOffset = QtCore.QPoint(0,0)

    # Guidelines - all on or off, opaque or feint
    @property
    def guidelinesVisible(self):
        return self._guidelinesVisible
    
    @guidelinesVisible.setter
    def guidelinesVisible(self,visible):
        visible = (visible==True)
        self._guidelinesVisible = visible
        for item in self.guidelineList:
            item.setVisible( visible )

    @property
    def guidelinesBright(self):
        return self._guidelinesBright
    
    @guidelinesBright.setter
    def guidelinesBright(self,bright):
        bright = (bright==True)
        self._guidelinesBright = bright
        opacity = 0.7 if bright else 0.3
        for item in self.guidelineList:
            item.setOpacity( opacity )

    # Crop offset - triggers redrawing of cropRect

    @property 
    def crop(self):
        return self._crop
    
    @crop.setter
    def crop(self, c ):
        offsetX, offsetY, w, h = c
        offset = QtCore.QPoint( *(offsetX,offsetY) )
        centre = self.perfRect.rect().center()
        perfPos = self.perfRect.pos()
        # Make sure we don't move off the edge of the image
        newX, newY = (perfPos+centre+offset).toTuple()
        newX = max( newX, 0 )
        newY = max( newY, 0 )
        self.cropRect.setPos( newX, newY )
        # Make sure we don't draw over the edge of the image
        x,y = self.cropRect.pos().toTuple()
        maxWidth = self.width()
        maxHeight = self.height()
        #w = min( x+w, maxWidth-x )
        #h = min( y+h, maxHeight-y )
        self.cropRect.setRect(0,0,w,h)
        self.updateHistRect()
        
    # Perforation rectangle

    @property
    def perforationRect(self):
        return self.perfRect.rect().toTuple()

    @perforationRect.setter
    def perforationRect(self,rect):
        print "setting perforation rect {}".format(rect)
        self.perfRect.setRect(*rect)
        self.perforationCentre = self.perfRect.rect().center()
        x,y = self.perforationCentre.toTuple()
        x1,y1 = self.ROIcentre.toTuple()
        self.vDiffLine.setLine( x,y,x,y1 )
    
    # ROI rectangle
    
    @property
    def roiRect(self):
        return self._roiRect

    @roiRect.setter
    def roiRect(self,rect):
        x,y,w,h = rect
        print("Setting ROI rectangle: {}".format(rect))
        self._roiRect = rect
        self.ROIrect.setPos( x,y )
        self.ROIrect.setRect( 0,0,w,h )
        self.ROIcentre = self.ROIrect.rect().center() + self.ROIrect.pos()
        print self.ROIcentre

    # Image

    @property 
    def mainPixmap(self):
        return self.pixmap.pixmap()
    
    @mainPixmap.setter
    def mainPixmap(self,qimg):
        self.pixmap.setPixmap( QtGui.QPixmap.fromImage(qimg) )
        self.setSceneRect( QtCore.QRectF(0,0,qimg.width(),qimg.height()) )
        
    @property
    def clipPixmap(self):
        return self.clippedPixmap.pixmap()
    
    @clipPixmap.setter
    def clipPixmap(self,qimg):
        if type(qimg) == QtGui.QImage:
            # display clipped pixmap and make visible
            self.clippedPixmap.setPixmap( QtGui.QPixmap.fromImage(qimg) )
            self.clippedPixmap.setVisible(True)
        else:
            self.clippedPixmap.setVisible(False)

    def mouseDoubleClickEvent(self,event):
        # Emits the integer coordinates of a double-click
        pos = event.scenePos().toPoint().toTuple()
        print( "Doubleclicked on scene: {}".format(pos) )
        self.doubleClicked.emit( pos )

    @property
    def histCropProportion(self):
        return self._histCropProportion


    def updateHistArea(self,val):
        self.histRectProportion = float(val) / 100
        self.updateHistRect()

    def updateHistRect(self):
        # Set histogram rectangle inside crop rectangle
        w,h = self.cropRect.rect().size().toTuple()
        x,y = self.cropRect.pos().toTuple()
        hw, hh = w*self.histRectProportion, h*self.histRectProportion
        hx, hy = x+((w-hw)/2), y+((h-hh)/2)
        self.histRect.setPos( hx,hy )
        self.histRect.setRect( 0,0,hw,hh )
        self.histRectChanged.emit()

    def getHistogramRect(self):
        # Returns histogram rectangle
        w,h = self.histRect.rect().size().toTuple()
        x,y = self.histRect.pos().toTuple()
        visible = self.histRect.isVisible()
        return (visible, x,y,w,h)

# This is the View of the preview scene - allows zooming and panning
class PreviewView( QtGui.QGraphicsView ):

    def __init__(self,scene=None,parent=None):
        super(PreviewView,self).__init__(scene,parent)
        # Mouse dragging to move preview
        self.setDragMode(QtGui.QGraphicsView.ScrollHandDrag)

        # Set an initial scale of 33%
        self.scale(0.33,0.33)
        self.centerOn(self.scene().pixmap)
        self.scaleFactor = 1.15

    def wheelEvent(self, event):
        # Use mouse for zooming the preview image and limit extents
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        if event.delta() > 0:
            self.zoomIn()
        else:
            self.zoomOut()

    def One2one(self):
        # Set the view to 100%
        self.setTransform(QtGui.QTransform.fromScale(1.0, 1.0))

    def fitToWindow(self):
        # Resize to fit image in view window
        self.fitInView(self.scene().pixmap, QtCore.Qt.KeepAspectRatio)

    def zoomIn(self):
        # Use mouse for zooming the preview image and limit extents
        if self.transform().m11() < 4.0: 
            self.scale(self.scaleFactor, self.scaleFactor);

    def zoomOut(self):
        if self.transform().m11() > 0.1:
            #Zoom out
            self.scale(1.0 / self.scaleFactor, 1.0 / self.scaleFactor)
            
#*******************************************************************************

class SetupJob( QtGui.QWidget ):

    # Signals
    filmTypeChanged = QtCore.Signal(str) # Emits new film type
    jobNameChanged = QtCore.Signal(str) # Emits a change of job name
    outputDirectoryChanged = QtCore.Signal(str) # Emits new output dir name
    finishedMovingFilm = QtCore.Signal() # finished moving film transport

    _transport = { 'stepsFwd':0, 'stepsBack':0, 'pixelsPerStep':0 }

    cropAspectRatio = None
    
    imageTaken = False # Prevents stuff happening before we have a picture

    def __init__(self,camera,tc,pf,parent=None):
        super(SetupJob, self).__init__(parent)

        self.camera = camera

        self.filmType = 'super8'
        self.pf = pf
        self.tc = tc

        self.perforationFound = False

        self.ui = Ui_SetupJobForm()
        self.ui.setupUi(self)
        self.statusbar = parent.ui.statusbar

        self.scene = PreviewScene()
        
        # Set up preview with blank image
        self.imageWidth, self.imageHeight = w,h = 1024,800
        self.previewImg = np.zeros( (h,w,3), dtype=np.uint8 )
        self.clippedImg = np.zeros( (h,w,3), dtype=np.uint8 )
        self.previewQimg = guiCommon.makeQimage(self.previewImg)
        self.scene.setSceneRect(0, 0, w, h)
        
        # Timer used so we don't constantly update histogram
        self.histogramTimer = QtCore.QTimer()
        self.histogramTimer.setSingleShot(True)
        self.histogramTimer.timeout.connect(self.makeHistogram)
        self.scene.histRectChanged.connect( self.makeHistogramDelayed )
        
        # Preview Window
        self.view = PreviewView(self.scene)
        self.ui.layoutPreview.insertWidget(0,self.view)
        self.ui.btnOne2one.clicked.connect( self.view.One2one )
        self.ui.btnZoomIn.clicked.connect( self.view.zoomIn )
        self.ui.btnZoomOut.clicked.connect( self.view.zoomOut )
        self.ui.btnFit.clicked.connect( self.view.fitToWindow )
       

        # Job Setup tab
        self.ui.btnChangeJobName.clicked.connect(self.changeJobName)
        self.ui.btnChooseDir.clicked.connect(self.chooseOutputDirectory)
        self.ui.btnChangeFilm.clicked.connect(self.changeFilmType)
        self.ui.spinShutter.valueChanged.connect( self.updateCameraShutterSpeed )
        self.ui.spinGainR.valueChanged.connect( self.updateCameraGains )
        self.ui.spinGainB.valueChanged.connect( self.updateCameraGains )
        self.ui.chkShowClipped.stateChanged.connect( self.makeClippedImage )

        # Crop toolbox disabled until we have first image
        self.ui.toolCrop.setEnabled( False )
        # Autocrop button only works after a perforation is available
        self.ui.btnAutoCrop.setEnabled( False )

        self.ui.cmbAspectFix.currentIndexChanged.connect( self.setAspectRatio )

        # Preview updater thread
        self.previewUpdater = CameraPreviewUpdater(self.camera,parent)
        self.previewUpdater.pictureReady.connect(self.updatePicture)
        self.previewUpdater.start()
        
        # Perforation checking options
        self.ui.radioTopEdge.toggled.connect(self.setCheckEdges)
        self.ui.radioBottomEdge.toggled.connect(self.setCheckEdges)
        self.ui.radioTopEdge.toggled.connect(self.setCheckEdges)
        self.ui.checkLeftEdge.stateChanged.connect(self.setLeftEdgeCheck)
        
        # Transport
        self.ui.btnStop.clicked.connect( self.stopAndCentre )
        self.ui.btnNudgeU.clicked.connect( self.nudgeFilmFwd )
        self.ui.btnNudgeD.clicked.connect( self.nudgeFilmBack )
        
        # Update or initialise perforation detection
        self.scene.doubleClicked.connect( self.locateFirstPerforation )
        
        # Film Transport
        self.finishedMovingFilm.connect( self.previewUpdater.updatePicture )
        self.transport = (285,285,3.5)
        self.ui.btnCalibrate.clicked.connect( self.calibrateTransport )

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
        f = ('Standard 8','Super 8') if self.filmType == 'std8' else ('Super 8','Standard 8')
        message = 'Are you sure you want to change<br>from <b>{}</b> to <b>{}</b> film?<br>Some settings will be reset.'.format(*f)
        reply = QtGui.QMessageBox.question(self, 'Message',message, QtGui.QMessageBox.Yes | 
            QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.Yes:
            f = 'super8' if self.filmType == 'std8' else 'std8'
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

    def initCropEditing(self):
        # Allow editing of crop position etc, size after we have first image
        x = self.ui.spinCropX.value()
        y = self.ui.spinCropY.value()
        w = self.ui.spinCropW.value()
        h = self.ui.spinCropH.value()
        self.scene.cropOffset = ( x,y )
        self.scene.cropSize = ( w,h )
        self.ui.toolCrop.setEnabled( True )
        self.ui.spinCropX.valueChanged.connect( self.updateCropRect )
        self.ui.spinCropY.valueChanged.connect( self.updateCropRect )
        self.ui.spinCropW.valueChanged.connect( self.updateCropWidth )
        self.ui.spinCropH.valueChanged.connect( self.updateCropHeight )
        self.ui.spinHistArea.valueChanged.connect( self.scene.updateHistArea )
        self.ui.btnAutoCrop.clicked.connect( self.autoCrop )

    @QtCore.Slot(np.ndarray)
    def updatePicture(self,img):
        # Updates the preview image and histogram
        print("Updating picture {}".format(id(img)))
        # keep preview image around to be able to recreate histogram
        self.previewImg = img
        self.imageHeight, self.imageWidth = img.shape[:2]
        if not( self.imageTaken ):
            # set up the crop for the first time
            self.imageTaken = True
            self.initCropEditing()
            self.setSpinBoxRange( self.ui.spinCropW, 200, self.imageWidth )
            self.setSpinBoxRange( self.ui.spinCropH, 200, self.imageHeight )

        print( 0,0,self.imageWidth,self.imageHeight )
        self.previewQimg = guiCommon.makeQimage(img)
        self.scene.mainPixmap = self.previewQimg
        self.locatePerforation()
        self.makeHistogramDelayed()
        self.makeClippedImage()

        
    def makeHistogramDelayed(self):
        if self.histogramTimer.isActive():
            # reset and restart timer
            self.histogramTimer.stop()
        self.histogramTimer.start(250)

    def makeHistogram(self):
        # Makes the histogram from the image based on rect in preview scene
        # But only do so if the timer isn't running
        visible, x,y,w,h = self.scene.getHistogramRect()
        if visible:
            img = self.previewImg[y:y+h,x:x+w]
            hist = guiCommon.makeHistImage(img)
        else:
            hist = guiCommon.makeHistImage(self.previewImg)
        print("Make histogram v:{} x:{} y:{} w:{} h:{} shape:{}".format(visible, x,y,w,h,hist.shape))
        self.histqi = guiCommon.makeQimage(hist)
        self.ui.lblHistogram.setPixmap(QtGui.QPixmap.fromImage(self.histqi))
        
    def makeClippedImage(self, state=0):
        # Makes an image of clipped pixels - i.e 254/255 using OpenCV
        if self.ui.chkShowClipped.isChecked():
            ret,img = cv2.threshold(self.previewImg,254,255,cv2.THRESH_BINARY)
            #mask = (img.sum( axis=2 )>0)*255 # Make a transparency mask
            #img = np.dstack([img,mask])
            self.clippedImg = img
            self.clippedQimg = guiCommon.makeQimage(img)
            self.scene.clipPixmap = self.clippedQimg
            #self.scene.updateClippedPixmap(self.clippedQimg)
        else:
            self.scene.clipPixmap = None
            #self.scene.updateClippedPixmap(None)

    def setAspectRatio(self,idx):
        txt = self.ui.cmbAspectFix.itemText(idx)
        if txt == "4:3":
            self.cropAspectRatio = 4.0/3.0
        elif txt == "16:9":
            self.cropAspectRatio = 16.0/9.0
        else:
            self.cropAspectRatio = None
        self.updateCropHeight( self.ui.spinCropH.value() )
    
    '''
    Crop handling
    Setting the crop is available when there is a perforation, as the crop
    is based on an offset from the centre of the perforation
    '''
    @property
    def crop( self ):
        x = self.ui.spinCropX.value()
        y = self.ui.spinCropY.value()
        w = self.ui.spinCropW.value()
        h = self.ui.spinCropH.value()
        ha = self.ui.spinHistArea.value()
        return (x,y,w,h,ha) 

    @crop.setter
    def crop( self, crop ):
        x,y,w,h,ha = crop
        print "Setting Crop: {}".format(crop)
        # Set up crop controls
        self.ui.spinCropX.setValue( x )
        self.ui.spinCropY.setValue( y )
        self.ui.spinCropW.setValue( w )
        self.ui.spinCropH.setValue( h )
        self.ui.spinHistArea.setValue( ha )
        self.updateCropRect()
    
    def setSpinBox(self,sb,val):
        # Update a spinbox without sending the changed signals
        sb.blockSignals(True)
        sb.setValue(val)
        sb.blockSignals(False)
    
    def setSpinBoxRange( self, sb, low, high ):
        sb.blockSignals(True)
        sb.setRange( low, high )
        sb.blockSignals(False)
    
    def updateCropWidth(self,w):
        # called on change of size
        maxW = self.imageWidth
        print "updating W: maxW {}".format(maxW)
        if type(self.cropAspectRatio) is float:
            print "update width aspect"
            h = w // self.cropAspectRatio
            self.setSpinBox( self.ui.spinCropH, h )
        self.updateCropRect()

    def updateCropHeight(self,h):
        # called on change of size
        maxH = self.imageHeight
        print "updating H: maxH {}".format(maxH)
        if type(self.cropAspectRatio) is float:
            print "update height aspect"
            w = h * self.cropAspectRatio
            self.setSpinBox( self.ui.spinCropW, w )
        self.updateCropRect()

    def updateCropRect(self,val=0):
        # updates crop rectangle from UI, sets limits
        # updates offset to centre of perforation rectangle
        if not( self.imageTaken ):
            # Dont need to do this until we have a preview image
            return
         # Set crop in the preview
        self.scene.crop = ( self.ui.spinCropX.value(), 
                            self.ui.spinCropY.value(),
                            self.ui.spinCropW.value(),
                            self.ui.spinCropH.value() )

    def autoCrop(self):
        # Calculate a crop size and position based on the size of the perforation
        print "Auto crop rect"
        if not( self.imageTaken ) and not( self.pf.found ):
            # Dont need to do this until we have a preview image
            return
        x,y = self.pf.position
        cx, cy = self.pf.centre
        w,h = self.pf.expectedSize
        cropH = int(h * self.pf.frameHeightMultiplier[self.filmType]*1.05)
        cropW = int(w * self.pf.frameWidthMultiplier[self.filmType]*1.05)
        # Work out the offset
        cropX = w // 2
        if self.filmType == 'super8':
            cropY = 0 - cropH//2
        else:
            cropY = 0
        self.setSpinBox( self.ui.spinCropX, cropX )
        self.setSpinBox( self.ui.spinCropY, cropY )
        self.setSpinBox( self.ui.spinCropW, cropW )
        self.setSpinBox( self.ui.spinCropH, cropH )
        self.updateCropRect()
        
    @property
    def perforation(self):
        filmType = self.pf.filmType
        cx = self.pf.ROIcentrexy[0]
        w, h = self.pf.expectedSize
        return ( filmType, int(cx), int(w), int(h) )

    @perforation.setter
    def perforation(self,settings):
        filmType, cx, w, h = settings
        cam_crop = self.camera.camera_crop
        imageSize = cam_crop[2:]
        expectedSize = (w,h)
        self.pf.init( filmType, imageSize,expectedSize,int(cx) )
        print "expectedSize: {}".format(expectedSize)
        
    @property
    def checkEdges(self):
        if self.ui.radioTopBotEdge.isChecked():
            return 0
        elif self.ui.radioTopEdge.isChecked():
            return 1
        elif self.ui.radioBottomEdge.isChecked():
            return 2
    
    @checkEdges.setter
    def checkEdges(self,val):
        if val==0:
            self.ui.radioTopBotEdge.setChecked(True)
        elif val==1:
            self.ui.radioTopEdge.setChecked(True)
        elif val==2:
            self.ui.radioBottomEdge.setChecked(True)
        self.pf.checkEdges = val
    
    @QtCore.Slot()
    def setCheckEdges(self):
        self.pf.checkEdges = self.checkEdges
    
    @property
    def checkLeftEdge(self):
        return self.ui.checkLeftEdge.isChecked()
    
    @checkLeftEdge.setter
    def checkLeftEdge(self,val):
        self.ui.checkLeftEdge.setChecked(val)
        self.pf.checkLeftEdge = val

    @QtCore.Slot()
    def setLeftEdgeCheck(self):
        self.pf.checkLeftEdge = self.checkLeftEdge
            
    def locateFirstPerforation(self, pos ):
        # Do an initial perforation find based on the supplied coordinates
        self.pf.findFirstFromCoords( self.previewImg, pos, 20 )
        if self.pf.found:
            x,y = self.pf.position
            w,h = self.pf.expectedSize
            # Now do a normal find
            self.locatePerforation()
            self.pf.find( self.previewImg )
            self.ui.toolPerforation.setEnabled( self.pf.found )
            if self.pf.found:
                print "Perforation found: {} {}".format(self.pf.position,self.pf.expectedSize)
                text = "<b>Perforation found</b><br><br>Centre: {} Size: {}".format(self.pf.position,self.pf.expectedSize)
            else:
                text = "<b>Perforation not found</b><br><br>Try adjusting exposure and double clicking again in the centre of the perforation."
            self.ui.lblPerforationInfo.setText(text)



    def locatePerforation(self):
        # enable user interface to edit perforation
        pf = self.pf
        with Timer() as t:
            pf.find( self.previewImg )
        print "=> elasped perforation find: %s ms" % t.msecs
        cx = self.pf.centre[0] if self.pf.found else self.pf.ROIcentrexy[0]
        cy = self.pf.centre[1] if self.pf.found else self.pf.ROIcentrexy[1]
        self.setSpinBoxRange( self.ui.spinCropX, 0-cx, self.imageWidth )
        self.setSpinBoxRange( self.ui.spinCropY, 0-(cy*1.5), self.imageHeight )
        if pf.found:
            print "Perforation found: {} {} yDiff:{}".format(self.pf.position,self.pf.expectedSize,self.pf.yDiff)
            text = "<b>Perforation found</b><br><br>Centre: {} Size: {}".format(self.pf.position,self.pf.expectedSize)
            self.scene.roiRect = pf.ROIxy + pf.ROIwh
            self.scene.perforationRect = pf.position + pf.expectedSize
            self.updateCropRect()
            self.scene.guidelinesBright = True
            self.scene.guidelinesVisible = True
            self.ui.btnAutoCrop.setEnabled(True)
            self.ui.btnCalibrate.setEnabled(True)
            
        else:
            text = "<b>Perforation not found</b><br><br>Try adjusting exposure or film position."
            self.scene.guidelinesBright = False
            self.ui.btnAutoCrop.setEnabled(False)
            self.ui.btnCalibrate.setEnabled(False)

        self.ui.lblPerforationInfo.setText(text)


    def nudgeFilmFwd( self ):
        # Nudge film a few steps
        print("Nudge forward")
        self.tc.steps_forward(20)
        self.finishedMovingFilm.emit()
        
    def nudgeFilmBack( self ):
        print("Nudge backward")
        self.tc.steps_back(20)
        self.finishedMovingFilm.emit()
        
    @property
    def transport(self):
        stepsFwd = self._transport['stepsFwd']
        stepsBack = self._transport['stepsBack'] 
        pixelsPerStep = self._transport['pixelsPerStep']
        return ( stepsFwd, stepsBack, pixelsPerStep )

    @transport.setter
    def transport(self,val):
        stepsFwd, stepsBack, pixelsPerStep = val
        self.stepsFwd = stepsFwd
        self.stepsBack = stepsBack
        self.pixelsPerStep = pixelsPerStep

    @property
    def stepsFwd(self):
        return self._transport['stepsFwd']
    
    @stepsFwd.setter
    def stepsFwd(self,val):
        self._transport['stepsFwd'] = val
        self.ui.lblStepsFrameFwd.setText( "{}".format(val) )

    @property
    def stepsBack(self):
        return self._transport['stepsBack']
    
    @stepsBack.setter
    def stepsBack(self,val):
        self._transport['stepsBack'] = val
        self.ui.lblStepsFrameBack.setText( "{}".format(val) )

    @property
    def pixelsPerStep(self):
        return self._transport['pixelsPerStep']
    
    @pixelsPerStep.setter
    def pixelsPerStep(self,val):
        val = min(10, max(0.25,val) )
        self._transport['pixelsPerStep'] = val
        self.ui.lblStepsPixel.setText( "{:.2f}".format(val) )


    def centreFrame(self, usePixelsPerStep=True):
        # Attempt to centre the frame on the perforation 
        # Get it within +/- 10 pixels of the centre
        done = False
        count = 10
        print('Centering')
        if usePixelsPerStep:
            pixelsPerStep = self.pixelsPerStep
        else:
            pixelsPerStep = 8 # Assume a fairly safe value
        while (count > 0) and not done:
            count -= 1
            img = self.camera.take_picture()
            self.pf.find(img)
            if self.pf.found:
                stepsDiff = int( max(5,abs(self.pf.yDiff/pixelsPerStep)))
                print( 'yDiff: {} stepsDiff: {}'.format( self.pf.yDiff, stepsDiff ) )
                if self.pf.yDiff > 5:
                    self.tc.steps_forward( stepsDiff )
                elif self.pf.yDiff < -5:
                    self.tc.steps_back( stepsDiff )
                else:
                    # Pretty close to the centre
                    done = True
            else:
                # No perforation found so step forward a larger number 
                # of steps to get a perforation into the ROI
                self.tc.steps_forward( 60 )

    def displayText( self, text, label=None ):
        if label != None:
            label.setText( 'Please wait...' )
            print( text )
            label.repaint()
            QtGui.QApplication.processEvents()
            time.sleep(0.005)

    def stepsPerFrame(self,frames=18,d=True,label=None):
        pf = self.pf
        tc = self.tc
        camera = self.camera
        self.displayText( 'Please wait...', label )
        tc.tension_film()
        self.centreFrame( usePixelsPerStep=False )
        if not pf.found:
            self.displayText( "No perforation available", label )
            return 0
        longStep = 50
        shortStep = 10
        counts = []
        steps = 0
        # Get an estimate for a first frame
        # move until perforation is no longer detected
        while pf.found:
            tc.steps_forward(longStep) if d else tc.steps_back(longStep)
            steps += longStep
            img = camera.take_picture()
            pf.find( img )
        # now move until we find perforation
        while not pf.found:
            tc.steps_forward(longStep) if d else tc.steps_back(longStep)
            steps += longStep
            img = camera.take_picture()
            pf.find( img )
        # Take short steps until it's close to the centre
        if d:
            while pf.yDiff > 0:
                tc.steps_forward( shortStep )
                steps += shortStep
                img = camera.take_picture()
                pf.find( img )
        else:
            while pf.yDiff < 0:
                tc.steps_back( shortStep )
                steps += shortStep
                img = camera.take_picture()
                pf.find( img )
        counts.append( steps )
        pixelsPerFrame = pf.expectedSize[1]*pf.frameHeightMultiplier[ pf.filmType ]
        self.pixelsPerStep = pixelsPerFrame / steps
        # Now refine over a number of frames
        failures = 0
        tc.tension_film()
        while len(counts) < frames and failures < 3:
            self.displayText( "{} of {}".format(len(counts),frames), label )
            self.centreFrame()
            tc.steps_forward( steps ) if d else tc.steps_back( steps )
            img = camera.take_picture()
            pf.find( img )
            if pf.found:
                correction = pf.yDiff / self.pixelsPerStep
                if d:
                    steps += correction 
                else:
                    steps -= correction
                counts.append( steps )
                print "**** framesteps:{}".format(steps)
            else:
                failures += 1
                print "**** failed :-("
        if failures < 3:
            #aveSteps = int(round(sum(counts)/float(len(counts))))
            aveSteps = np.median(counts)
            print('Steps per frame:')
            print('Ave steps over {} frames is {}'.format(len(counts),aveSteps))
            print('Min:{} Max:{}'.format(min(counts),max(counts)))
            print counts
            return int( round(aveSteps) )
        else:
            return 0

    def calibrateTransport(self):
        # Calibrate the film transport over a number of frames
        # This establishes how many motor steps are needed on average
        # for a sequence of frames. d=True - move forwards, else move backward
        pf = self.pf
        self.ui.btnCalibrate.setEnabled(False)
        #steps per frame forward
        fwd = self.stepsPerFrame( frames=18, d=True, label=self.ui.lblStepsFrameFwd )
        if fwd > 0: 
            self.stepsFwd = fwd
            # Refine steps per pixel
            pixelsPerFrame = pf.expectedSize[1]*pf.frameHeightMultiplier[pf.filmType]
            pxFwd = pixelsPerFrame / fwd
            #steps per frame back
            back = self.stepsPerFrame( frames=18, d=False, label=self.ui.lblStepsFrameBack )
            if back > 0: 
                self.stepsBack = back
                pxBack = pixelsPerFrame / back
                self.pixelsPerStep = (pxFwd + pxBack) / 2
            else:
                self.ui.lblStepsFrameBack.setText('Failed...')
        else:
            self.ui.lblStepsFrameFwd.setText('Failed...')
 
        self.ui.btnCalibrate.setEnabled(True)
        #self.centreFrame()
        self.finishedMovingFilm.emit()

    
            
    def stopAndCentre(self):
        self.centreFrame()
        self.finishedMovingFilm.emit()
        
    